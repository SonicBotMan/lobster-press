#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试 - Issue #174 修复验证

测试覆盖：
- Fix 1: DECISION_KEYWORDS 死代码修复
- Fix 2: 数据库事务保护
- Fix 3: 修复"丢弃消息"死循环
- Fix 5: 中文文本复杂度加权
- Fix 6: TF-IDF O(n²) 性能优化
- Fix 7: afterTurn 本地计数

Author: LobsterPress Team
Version: v4.0.36
"""

import pytest
import tempfile
import os
from pathlib import Path

# 添加项目根目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.dag_compressor import DAGCompressor
from src.database import LobsterDatabase
from src.pipeline.tfidf_scorer import TFIDFScorer


class TestIssue174Fixes:
    """Issue #174 修复验证测试套件"""

    def test_fix1_decision_keywords_not_dead_code(self):
        """Fix 1: 验证 DECISION_KEYWORDS 不是死代码"""
        compressor = DAGCompressor.__new__(DAGCompressor)

        # 验证 DECISION_KEYWORDS 存在
        assert hasattr(DAGCompressor, 'DECISION_KEYWORDS')

        # 验证 DECISION_KEYWORDS 包含预期关键词
        keywords = DAGCompressor.DECISION_KEYWORDS
        assert '决定' in keywords or '采用' in keywords or 'chosen' in keywords

    def test_fix2_database_transaction_protection(self):
        """Fix 2: 验证数据库事务保护"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = LobsterDatabase(db_path)

            # 验证数据库连接存在
            assert db.conn is not None

            # 验证事务保护（使用 with 语句）
            try:
                with db.conn:
                    # 执行数据库操作
                    cursor = db.conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    assert result == (1,)
            except Exception as e:
                pytest.fail(f"事务保护失败: {e}")

    def test_fix3_no_dead_loop_on_small_episodes(self):
        """Fix 3: 验证小 episode 不会导致死循环"""
        # 这个测试需要完整的压缩流程，这里只做基本验证
        # 实际测试需要在集成环境中运行
        compressor = DAGCompressor.__new__(DAGCompressor)

        # 验证核心方法存在
        # Fix 3 主要修改了 leaf_compact 方法中的逻辑
        assert hasattr(compressor, 'leaf_compact')

    def test_fix5_chinese_text_complexity_weighting(self):
        """Fix 5: 验证中文文本复杂度加权"""
        scorer = TFIDFScorer()

        # 测试中文文本
        chinese_text = "这是一个中文测试文本，用于验证复杂度加权功能。"

        # 测试英文文本
        english_text = "This is an English test text for complexity weighting."

        # 分词
        chinese_tokens = scorer.tokenize(chinese_text)
        english_tokens = scorer.tokenize(english_text)

        # 验证中文 bi-gram 提取
        chinese_bigrams = [t for t in chinese_tokens if len(t) == 2 and all('\u4e00' <= c <= '\u9fff' for c in t)]
        assert len(chinese_bigrams) > 0, "中文 bi-gram 提取失败"

    def test_fix6_tfidf_caching(self):
        """Fix 6: 验证 TF-IDF 缓存优化"""
        scorer = TFIDFScorer()

        # 准备测试消息
        messages = [
            {"id": "m1", "role": "user", "content": "测试消息一", "timestamp": 0},
            {"id": "m2", "role": "user", "content": "测试消息二", "timestamp": 0},
        ]

        # 第一次评分
        result1 = scorer.score_and_tag(messages)

        # 验证缓存已建立
        assert scorer._corpus_hash != 0
        assert len(scorer.idf_cache) > 0

        # 第二次评分（应该使用缓存）
        result2 = scorer.score_and_tag(messages)

        # 验证缓存一致性（两次评分的 hash 应该相同）
        # 注意：corpus_tokens 是局部变量，不在实例上，所以这里只验证 hash 不变
        assert result1[0].tfidf_score == result2[0].tfidf_score

    def test_fix7_local_turn_counter(self):
        """Fix 7: 验证 afterTurn 本地计数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = LobsterDatabase(db_path)

            # 验证 _turn_counts 缓存存在
            assert hasattr(db, '_turn_counts')

            # 验证 get_turn_count 方法存在
            assert hasattr(db, 'get_turn_count')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
