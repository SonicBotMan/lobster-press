# Python API 参考（v5.1.1）

> 本文档所有示例已在 v5.1.1 真实执行验证。

## LobsterDatabase

```python
import os
from src.database import LobsterDatabase

# 注意：构造函数不展开 ~，必须用 expanduser（或直接给绝对路径）
db = LobsterDatabase(os.path.expanduser("~/.openclaw/lobster.db"))
conversation_id = db.create_conversation("my-agent")
db.add_message(conversation_id, "user", "决定采用 PostgreSQL 作为主存储")

# 全文搜索（trigram；<3 字符自动 LIKE 回退）
results = db.search_messages("PostgreSQL", conversation_id)
```

## IncrementalCompressor（自动压缩入口）

```python
import os
from src.database import LobsterDatabase
from src.incremental_compressor import IncrementalCompressor

db = LobsterDatabase(os.path.expanduser("~/.openclaw/lobster.db"))
manager = IncrementalCompressor(db)

# 消息 dict 需带 id 字段（入库主键）；不带时由存储层自动生成
result = manager.on_new_message(
    conversation_id="conv_x",
    message={"id": "msg_001", "role": "user", "content": "..."},
)

# 返回契约（v5.1.1 实测）：
# - 上下文使用率未达 contextThreshold → 返回 None
# - 达到阈值 → 返回 dict，但键随策略不同：
#     none / light 策略 → {strategy, usage_ratio, messages_compressed, tokens_saved}
#     aggressive (DAG)  → {leaf_summaries, condensed_summaries, messages_compressed,
#                          tokens_saved[, notes_extracted]}
# 因此消费方务必按"键可能不存在"防御：
if result is not None:
    print(f"压缩 {result.get('messages_compressed', 0)} 条，"
          f"省 {result.get('tokens_saved', 0)} tokens"
          + (f"，策略 {result['strategy']}" if "strategy" in result else "（DAG 压缩）"))
```

### 构造参数（默认值 = 代码默认，v5.1.1）

| 参数 | 默认 | 说明 |
|------|------|------|
| `context_threshold` | `0.75` | 上下文使用率压缩阈值 |
| `max_context_tokens` | `128_000` | 上限（Claude 200K / Gemini 1M 用户可调高） |

策略分界：使用率 `<0.60` 不压缩、`<0.75` light（语义去重）、`≥0.75` aggressive（DAG 压缩）。

## agent_tools（函数式 API）

```python
from src.agent_tools import lobster_grep, lobster_describe, lobster_expand

hits = lobster_grep(db, "PostgreSQL", conversation_id=conversation_id, limit=5)
tree = lobster_describe(db, conversation_id=conversation_id)   # keys: total_summaries/max_depth/by_depth
raw  = lobster_expand(db, summary_id=tree and "sum_xxx")
```

## Viewer Web UI

```python
from src.viewer.server import start_viewer

server = start_viewer(db, port=18799, password="mypassword")
server.serve_forever()  # v5.1.1 注意：start_viewer 只构造不启动，必须显式 serve_forever()
```

## 语义笔记 + 矛盾检测

```python
from src.semantic_memory import SemanticMemory
from src.pipeline.conflict_detector import ConflictDetector

sm = SemanticMemory(db)
sm.extract_and_store(conversation_id=conversation_id, ...)     # LLM 提取结构化笔记

det = ConflictDetector(use_nli=True)   # NLI 模型缺失时自动回退规则检测
conflicts = det.detect(
    new_message={"content": "不再使用 PostgreSQL 了，改用 MongoDB"},
    existing_notes=[{"note_id": "n1", "content": "决定采用 PostgreSQL 作为主存储"}],
)
# v5.1.1：规则层要求旧主张含明确采用动词（采用/使用/决定用/deploy...），
# "the user likes react" 这类偏好陈述不再误报
```

## 遗忘曲线公式

`R(t) = 0.5^(t / half_life)`（v5.1.1 修正，弃用旧 `e^(-t/h)` 实现）。
压缩半衰期按消息类型 3–120 天（chitchat 最短），检索半衰期固定 14 天，地板系数 0.3。

> ⚠️ 历史注意：早期版本的 `LobsterDatabase("~/.openclaw/lobster.db")` 写法中波浪号不会展开——自 v5.1.1 起文档统一使用 `expanduser`，老代码请自查。
