# Issue #164: TS<->Python 跨层契约测试设计

> **For agent:** REQUIRED SUB-SKILL: Use Section 4 or Section 5 to implement this plan.

**Goal:** 为所有 15 个 MCP 工具添加响应结构验证，防止协议边界漂移（protocol drift）

**Architecture:** 创建 `tests/contract/` 目录，为每个 MCP 工具创建独立的契约测试文件，使用 pytest fixtures 模拟 MCP 调用，验证响应字段存在、类型正确、边界情况处理

**Tech Stack:** Python 3.10+, pytest, pytest-asyncio, dataclasses

---

## 1. 背景与目标

### 背景
v4.0.20-v4.0.24 的连续修复都是因为 TS 和 Python 两侧对 MCP 响应的 shape 假设不同步导致的，属于"协议边界漂移"（protocol drift）。

### 目标
- 为每个 MCP 工具添加响应结构验证
- 确保关键字段存在且类型正确
- 防止未来再次出现类似的 MCP 响应结构不同步问题

---

## 2. MCP 工具列表（15 个）

根据 `mcp_server/lobster_mcp_server.py`，需要测试的 MCP 工具：

1. **compress_session** - 压缩会话
2. **preview_compression** - 预览压缩
3. **get_compression_stats** - 获取压缩统计
4. **update_weights** - 更新权重
5. **list_sessions** - 列出会话
6. **lobster_grep** - 全文搜索
7. **lobster_describe** - 查看 DAG 结构
8. **lobster_expand** - 展开摘要
9. **lobster_compress** - 增量压缩
10. **lobster_assemble** - 拼装上下文
11. **lobster_correct** - 记忆纠错
12. **lobster_sweep** - 清理衰减消息
13. **lobster_status** - 系统健康报告
14. **lobster_prune** - 删除衰减消息
15. **lobster_ingest** - 消息入库

---

## 3. 架构设计

### 3.1 目录结构

```
tests/
├── contract/
│   ├── __init__.py
│   ├── conftest.py                    # 共享 fixtures
│   ├── test_compress_session_contract.py
│   ├── test_preview_compression_contract.py
│   ├── test_get_compression_stats_contract.py
│   ├── test_update_weights_contract.py
│   ├── test_list_sessions_contract.py
│   ├── test_lobster_grep_contract.py
│   ├── test_lobster_describe_contract.py
│   ├── test_lobster_expand_contract.py
│   ├── test_lobster_compress_contract.py
│   ├── test_lobster_assemble_contract.py
│   ├── test_lobster_correct_contract.py
│   ├── test_lobster_sweep_contract.py
│   ├── test_lobster_status_contract.py
│   ├── test_lobster_prune_contract.py
│   └── test_lobster_ingest_contract.py
```

### 3.2 测试模式

每个契约测试文件遵循以下模式：

```python
import pytest
from dataclasses import asdict

class TestToolNameContract:
    """契约测试：验证 MCP 工具响应结构"""
    
    @pytest.fixture
    def mock_mcp_server(self):
        """创建模拟的 MCP 服务器"""
        # ...
    
    def test_response_has_required_fields(self, mock_mcp_server):
        """验证响应包含必需字段"""
        # ...
    
    def test_response_field_types(self, mock_mcp_server):
        """验证响应字段类型正确"""
        # ...
    
    def test_edge_cases(self, mock_mcp_server):
        """验证边界情况处理"""
        # ...
```

### 3.3 响应结构验证

根据 TS 侧的解析逻辑（`content[0].text` → JSON.parse），验证以下结构：

```python
{
    "content": [
        {
            "type": "text",
            "text": "<JSON 字符串>"
        }
    ]
}
```

解析后的 JSON 对象必须包含工具特定的字段。

---

## 4. 实施策略

### 4.1 优先级分组

**P0（高风险，先实现）**：
- lobster_compress
- lobster_assemble
- lobster_ingest

**P1（中等风险）**：
- lobster_grep
- lobster_describe
- lobster_expand
- lobster_status

**P2（低风险）**：
- compress_session
- preview_compression
- get_compression_stats
- update_weights
- list_sessions
- lobster_correct
- lobster_sweep
- lobster_prune

### 4.2 每个测试文件的验证点

1. **响应字段存在**：验证必需字段是否存在
2. **字段类型正确**：验证字段类型（string, integer, boolean, array, object）
3. **边界情况**：
   - 空输入
   - 无效参数
   - 不存在的 ID
   - 权限错误

---

## 5. CI 集成

### 5.1 修改 `.github/workflows/test.yml`

添加契约测试阶段：

```yaml
- name: Run contract tests
  run: |
    python -m pytest tests/contract/ -v --tb=short
```

### 5.2 测试运行顺序

1. 单元测试（tests/unit/）
2. 契约测试（tests/contract/）← 新增
3. 集成测试（tests/integration/）

---

## 6. 验收标准

- [ ] 所有 15 个 MCP 工具都有对应的契约测试文件
- [ ] 每个测试文件包含至少 3 个测试用例（必需字段、类型、边界情况）
- [ ] 所有测试在 CI 中通过
- [ ] 测试覆盖率 ≥ 90%（针对响应结构验证）
- [ ] 文档更新（README.md 中说明契约测试的存在）

---

## 7. 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 测试过多影响 CI 速度 | 使用 pytest-xdist 并行运行 |
| Mock 数据与真实响应不一致 | 定期从真实 MCP 调用中更新 fixture 数据 |
| 契约测试无法覆盖所有边界情况 | 结合集成测试，契约测试只验证结构 |

---

## 8. 时间估算

- P0 工具（3 个）：2-3 小时
- P1 工具（4 个）：2-3 小时
- P2 工具（8 个）：3-4 小时
- CI 集成 + 文档：1 小时

**总计**：8-11 小时

---

## 9. 关联

- Issue: #164
- 来源: #162 Risk #2
- Perplexity 评估: 协议边界漂移风险
