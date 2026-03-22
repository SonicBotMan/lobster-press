# Issue #164: 契约测试实施计划

> **For agent:** REQUIRED SUB-SKILL: Use Section 4 or Section 5 to implement this plan.

**Goal:** 为所有 15 个 MCP 工具添加响应结构验证

**Architecture:** 创建 `tests/contract/` 目录，每个工具一个测试文件

**Tech Stack:** Python 3.10+, pytest, pytest-asyncio

---

## 实施策略

**分 5 个阶段，共 17 个任务：**

1. **阶段 1**：创建测试框架（1 任务）
2. **阶段 2**：P0 工具（3 任务）- lobster_compress, lobster_assemble, lobster_ingest
3. **阶段 3**：P1 工具（4 任务）- lobster_grep, lobster_describe, lobster_expand, lobster_status
4. **阶段 4**：P2 工具（8 任务）- 其他工具
5. **阶段 5**：CI 集成（1 任务）

---

## Task 1: 创建测试框架

**Files:**
- Create: `tests/contract/__init__.py`
- Create: `tests/contract/conftest.py`

**Step 1:** 创建 `tests/contract/__init__.py`
```python
# tests/contract/__init__.py
"""契约测试：验证 MCP 工具响应结构"""
```

**Step 2:** 创建 `tests/contract/conftest.py`（共享 fixtures）

```python
# tests/contract/conftest.py
import pytest
import tempfile
import os
from pathlib import Path
from src.database import LobsterDatabase
from src.dag_compressor import DAGCompressor
from mcp_server.lobster_mcp_server import LobsterMCPServer


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = LobsterDatabase(db_path)
        yield db
        db.close()


@pytest.fixture
def compressor(temp_db):
    """创建压缩器"""
    return DAGCompressor(
        db=temp_db,
        fresh_tail_count=5,
        leaf_chunk_tokens=500
    )


@pytest.fixture
def mcp_server(temp_db, compressor):
    """创建 MCP 服务器"""
    return LobsterMCPServer(db=temp_db, compressor=compressor)


@pytest.fixture
def sample_conversation_id():
    """示例对话 ID"""
    return "test_conv_123"


@pytest.fixture
def sample_messages():
    """示例消息列表"""
    return [
        {
            "message_id": "msg_1",
            "role": "user",
            "content": "你好，我想了解 LobsterPress",
            "timestamp": "2026-03-22T10:00:00Z",
            "token_count": 10
        },
        {
            "message_id": "msg_2",
            "role": "assistant",
            "content": "LobsterPress 是一个 AI 记忆压缩库",
            "timestamp": "2026-03-22T10:01:00Z",
            "token_count": 15
        }
    ]
```

**Step 3:** 运行测试验证 fixtures
```bash
python -m pytest tests/contract/conftest.py -v
```

**Expected output:**
```
============================= test session starts ==============================
collected 0 items
============================ no tests ran in 0.01s =============================
```

**Step 4:** 提交
```bash
git add tests/contract/
git commit -m "test: add contract test framework for Issue #164"
```

---

## Task 2: lobster_compress 契约测试

**Files:**
- Create: `tests/contract/test_lobster_compress_contract.py`

**Step 1:** 创建测试文件

```python
# tests/contract/test_lobster_compress_contract.py
import pytest
import json


class TestLobsterCompressContract:
    """契约测试：验证 lobster_compress 响应结构"""

    @pytest.mark.asyncio
    async def test_response_has_required_fields(self, mcp_server, sample_conversation_id):
        """验证响应包含必需字段"""
        # 准备数据：插入消息
        # 调用工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_compress",
                "arguments": {
                    "conversation_id": sample_conversation_id,
                    "token_budget": 8000
                }
            }
        })

        # 验证响应结构
        assert "content" in response
        assert isinstance(response["content"], list)
        assert len(response["content"]) > 0

        # 验证 content[0].text 格式
        content = response["content"][0]
        assert content["type"] == "text"
        assert "text" in content

        # 解析 JSON
        result = json.loads(content["text"])
        assert "compressed" in result
        assert isinstance(result["compressed"], bool)

    @pytest.mark.asyncio
    async def test_response_field_types(self, mcp_server, sample_conversation_id):
        """验证响应字段类型正确"""
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_compress",
                "arguments": {
                    "conversation_id": sample_conversation_id
                }
            }
        })

        result = json.loads(response["content"][0]["text"])

        # 验证字段类型
        if "tokens_saved" in result:
            assert isinstance(result["tokens_saved"], int)
        if "compression_ratio" in result:
            assert isinstance(result["compression_ratio"], (int, float))

    @pytest.mark.asyncio
    async def test_edge_case_empty_conversation(self, mcp_server):
        """验证边界情况：空对话"""
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_compress",
                "arguments": {
                    "conversation_id": "non_existent_conv"
                }
            }
        })

        # 应该返回成功响应，但 compressed=false
        result = json.loads(response["content"][0]["text"])
        assert result["compressed"] == False
```

**Step 2:** 运行测试
```bash
python -m pytest tests/contract/test_lobster_compress_contract.py -v
```

**Expected output:**
```
tests/contract/test_lobster_compress_contract.py::TestLobsterCompressContract::test_response_has_required_fields PASSED
tests/contract/test_lobster_compress_contract.py::TestLobsterCompressContract::test_response_field_types PASSED
tests/contract/test_lobster_compress_contract.py::TestLobsterCompressContract::test_edge_case_empty_conversation PASSED
============================= 3 passed in 0.15s ==============================
```

**Step 3:** 提交
```bash
git add tests/contract/test_lobster_compress_contract.py
git commit -m "test: add contract test for lobster_compress"
```

---

## Task 3-16: 其他工具契约测试

**遵循相同模式：**

每个工具的测试文件包含：
1. `test_response_has_required_fields` - 验证必需字段
2. `test_response_field_types` - 验证字段类型
3. `test_edge_case_*` - 验证边界情况

**P1 工具（Task 3-6）：**
- `test_lobster_assemble_contract.py`
- `test_lobster_ingest_contract.py`
- `test_lobster_grep_contract.py`
- `test_lobster_describe_contract.py`

**P2 工具（Task 7-16）：**
- `test_lobster_expand_contract.py`
- `test_lobster_status_contract.py`
- `test_compress_session_contract.py`
- `test_preview_compression_contract.py`
- `test_get_compression_stats_contract.py`
- `test_update_weights_contract.py`
- `test_list_sessions_contract.py`
- `test_lobster_correct_contract.py`
- `test_lobster_sweep_contract.py`
- `test_lobster_prune_contract.py`

---

## Task 17: CI 集成

**Files:**
- Modify: `.github/workflows/test.yml`

**Step 1:** 添加契约测试阶段

```yaml
# 在 test job 中添加
- name: Run contract tests
  run: |
    python -m pytest tests/contract/ -v --tb=short
```

**Step 2:** 运行 CI 验证
```bash
git add .github/workflows/test.yml
git commit -m "ci: add contract tests to CI pipeline"
git push
```

**Expected:** CI 通过，所有契约测试绿色

---

## 验收清单

- [ ] Task 1: 测试框架创建完成
- [ ] Task 2: lobster_compress 测试通过
- [ ] Task 3: lobster_assemble 测试通过
- [ ] Task 4: lobster_ingest 测试通过
- [ ] Task 5-8: P1 工具测试通过
- [ ] Task 9-16: P2 工具测试通过
- [ ] Task 17: CI 集成完成
- [ ] 所有测试在 CI 中通过
- [ ] 代码审查完成

---

## 时间估算

- Task 1: 30 分钟
- Task 2-4 (P0): 1.5 小时
- Task 5-8 (P1): 2 小时
- Task 9-16 (P2): 3 小时
- Task 17: 30 分钟

**总计**: 约 7.5 小时
