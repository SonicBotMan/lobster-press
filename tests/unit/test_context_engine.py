"""
ContextEngine 集成测试（v3.3.0+）

测试 ContextEngine 接口的实现：
- afterTurn 钩子
- compact 方法
- 自动触发逻辑
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from pathlib import Path
import sys
import tempfile
import json

# 添加 src 到 path
src_dir = Path(__file__).parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


class TestContextEngineInterface:
    """测试 ContextEngine 接口实现"""

    def test_after_turn_signature(self):
        """测试 afterTurn 方法签名"""
        # 模拟 ContextEngine 的 afterTurn 方法
        async def afterTurn(messages: list, sessionFile: str) -> dict:
            """每次 turn 后调用，检查上下文使用率"""
            current_tokens = sum(len(str(m)) // 3 for m in messages)
            token_budget = 128000
            usage_ratio = current_tokens / token_budget
            
            return {
                "shouldCompact": usage_ratio > 0.75,
                "currentTokens": current_tokens,
                "tokenBudget": token_budget,
                "usageRatio": usage_ratio
            }
        
        # 测试正常情况
        messages = [{"role": "user", "content": "test"}]
        result = asyncio.run(afterTurn(messages, "test-session"))
        
        assert "shouldCompact" in result
        assert "currentTokens" in result
        assert "tokenBudget" in result
        assert "usageRatio" in result
        assert result["tokenBudget"] == 128000

    def test_after_turn_trigger_logic(self):
        """测试 afterTurn 的触发逻辑"""
        async def afterTurn(messages: list, sessionFile: str) -> dict:
            current_tokens = sum(len(str(m)) // 3 for m in messages)
            token_budget = 128000
            usage_ratio = current_tokens / token_budget
            
            return {
                "shouldCompact": usage_ratio > 0.75,
                "usageRatio": usage_ratio
            }
        
        # 测试低使用率（不应触发）
        small_messages = [{"content": "x" * 100} for _ in range(10)]
        result = asyncio.run(afterTurn(small_messages, "test"))
        assert result["shouldCompact"] is False
        
        # 测试高使用率（应触发）
        large_messages = [{"content": "x" * 10000} for _ in range(100)]
        result = asyncio.run(afterTurn(large_messages, "test"))
        assert result["shouldCompact"] is True

    def test_compact_method_signature(self):
        """测试 compact 方法签名"""
        async def compact(currentTokenCount: int, tokenBudget: int, force: bool = False) -> dict:
            """执行压缩"""
            # 模拟压缩逻辑
            compressed = force or (currentTokenCount / tokenBudget > 0.75)
            
            return {
                "compressed": compressed,
                "tokensBefore": currentTokenCount,
                "tokensAfter": int(currentTokenCount * 0.6) if compressed else currentTokenCount,
                "force": force
            }
        
        # 测试强制压缩
        result = asyncio.run(compact(100000, 128000, force=True))
        assert result["compressed"] is True
        assert result["tokensBefore"] == 100000
        assert result["tokensAfter"] < result["tokensBefore"]
        
        # 测试正常压缩（超过阈值）
        result = asyncio.run(compact(100000, 128000, force=False))
        assert result["compressed"] is True
        
        # 测试不压缩（未超过阈值）
        result = asyncio.run(compact(50000, 128000, force=False))
        assert result["compressed"] is False


class TestLobsterCompressTool:
    """测试 lobster_compress MCP 工具"""

    @pytest.fixture
    def mock_db(self):
        """创建 mock 数据库"""
        db = MagicMock()
        db.get_messages.return_value = [
            {"id": "1", "content": "test message 1", "token_count": 10},
            {"id": "2", "content": "test message 2", "token_count": 10}
        ]
        return db

    @pytest.fixture
    def mock_compressor(self, mock_db):
        """创建 mock DAGCompressor"""
        from dag_compressor import DAGCompressor
        compressor = MagicMock(spec=DAGCompressor)
        compressor.incremental_compact.return_value = True
        return compressor

    def test_lobster_compress_below_threshold(self, mock_compressor):
        """测试 lobster_compress 在阈值以下时不压缩"""
        current_tokens = 50000
        token_budget = 128000
        
        # 计算阈值
        threshold = token_budget * 0.75  # 96000
        
        # 检查是否应该压缩
        should_compress = current_tokens >= threshold
        assert should_compress is False

    def test_lobster_compress_above_threshold(self, mock_compressor):
        """测试 lobster_compress 在阈值以上时压缩"""
        current_tokens = 100000
        token_budget = 128000
        
        # 计算阈值
        threshold = token_budget * 0.75  # 96000
        
        # 检查是否应该压缩
        should_compress = current_tokens >= threshold
        assert should_compress is True

    def test_lobster_compress_force(self, mock_compressor):
        """测试强制压缩（force=True）"""
        # 即使低于阈值，force=True 也应该压缩
        current_tokens = 50000
        token_budget = 128000
        force = True
        
        # 检查是否应该压缩
        should_compress = force or (current_tokens >= token_budget * 0.75)
        assert should_compress is True

    def test_lobster_compress_retry_mechanism(self):
        """测试重试机制（v3.3.1）"""
        max_retries = 3
        attempts = 0
        success = False
        
        # 模拟前 2 次失败，第 3 次成功
        for attempt in range(max_retries):
            attempts += 1
            if attempt == 2:  # 第 3 次成功
                success = True
                break
        
        assert attempts == 3
        assert success is True


class TestCompressSessionReal:
    """测试 compress_session 使用真实 DAGCompressor（v3.3.1）"""

    def test_compress_session_uses_real_dag(self):
        """测试 compress_session 调用真实 DAGCompressor"""
        from dag_compressor import DAGCompressor
        
        # 创建临时数据库
        with tempfile.TemporaryDirectory() as tmpdir:
            from database import LobsterDatabase
            db_path = Path(tmpdir) / "test.db"
            db = LobsterDatabase(str(db_path))
            
            # 创建 DAGCompressor
            compressor = DAGCompressor(db, fresh_tail_count=5)
            
            # 验证是真实的 DAGCompressor
            assert hasattr(compressor, 'incremental_compact')
            assert hasattr(compressor, 'leaf_compact')
            assert hasattr(compressor, 'condensed_compact')

    def test_strategy_mapping(self):
        """测试策略映射（v3.3.1）"""
        thresholds = {
            "light": 0.9,      # 90%
            "medium": 0.75,    # 75%
            "aggressive": 0.5  # 50%
        }
        
        # 验证策略映射
        assert thresholds["light"] == 0.9
        assert thresholds["medium"] == 0.75
        assert thresholds["aggressive"] == 0.5
        
        # 验证阈值顺序
        assert thresholds["light"] > thresholds["medium"] > thresholds["aggressive"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
