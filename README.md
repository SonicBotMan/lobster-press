<div align="center">

# 🦞 LobsterPress

**Python 原生的无损对话压缩库**  
*为任意 LLM Agent 框架提供永久记忆和智能上下文管理*

[![GitHub release](https://img.shields.io/github/release/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press/releases)
[![GitHub stars](https://img.shields.io/github/stars/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press)
[![GitHub license](https://img.shields.io/github/license/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)

**中文** | [English](README_EN.md)

**最新版本**: [v2.5.0](https://github.com/SonicBotMan/lobster-press/releases/tag/v2.5.0) · [更新日志](RELEASE_NOTES.md)

</div>

---

## 为什么需要 LobsterPress？

所有 LLM 都有上下文窗口限制。主流做法是滑动窗口截断——代价是旧对话永久丢失，Agent 变得"失忆"。

LobsterPress 采用 **无损 DAG 压缩**：每一条消息永久保存在本地 SQLite，通过分层摘要将历史折叠进上下文预算，同时保留完整的展开路径。**原始消息永远不会被删除。**

```
传统滑动窗口：  [msg 1..70 ❌ 丢弃]  [msg 71..100 保留]
LobsterPress：  [摘要 A → 摘要 B → msg 95..100]  ← 可展开回任意原始消息
```

### 与 lossless-claw 的核心区别

[lossless-claw](https://github.com/martian-engineering/lossless-claw) 是优秀的同类项目，LobsterPress 在以下维度做了差异化设计：

| | lossless-claw | LobsterPress |
|---|---|---|
| **运行环境** | OpenClaw 插件（Node.js） | 纯 Python，框架无关 |
| **压缩触发** | 单阈值（75%） | 三级阶梯（60% / 75% / 豁免） |
| **消息评分** | 无，所有消息平等对待 | TF-IDF + 结构化信号 + 时间衰减 |
| **关键信息保护** | 无 | `compression_exempt` 自动标记 |
| **迁移工具** | 无 | BatchImporter（JSON / CSV） |

> LobsterPress 不依赖任何特定 Agent 框架，可嵌入 LangChain、AutoGen、自建 Agent 或任何 Python 项目。

---

## 快速上手

```bash
git clone https://github.com/SonicBotMan/lobster-press.git
cd lobster-press
pip install -r requirements.txt
```

```python
from src.database import LobsterDatabase
from src.incremental_compressor import IncrementalCompressor

db = LobsterDatabase("memory.db")
manager = IncrementalCompressor(
    db,
    max_context_tokens=200_000,  # 按你的模型设置，如 Claude=200K，GPT-4o=128K
    context_threshold=0.75,
    fresh_tail_count=32
)

# 每轮对话后调用，自动决定是否压缩
result = manager.on_new_message("conv_id", {
    "id": "msg_001",
    "role": "user",
    "content": "我们决定用 PostgreSQL 作为主数据库",
    "timestamp": "2026-03-17T10:00:00Z"
})
# result["compression_strategy"] → "none" | "light" | "aggressive"
```

---

## 工作原理

### 三层压缩策略

```
上下文使用率        策略              LLM 调用成本
────────────────────────────────────────────────
< 60%              无操作            $0
60% – 75%          语义去重          $0   ← 零 API 调用
> 75%              DAG 摘要压缩      $    ← 调用 LLM 生成摘要
```

`light` 阶段通过余弦相似度去除冗余消息，无需调用 LLM，在密集对话场景可将摘要 API 调用频率显著降低。

### TF-IDF 评分 + 自动豁免

每条消息入库时自动计算 TF-IDF 分数并识别消息类型：

```
"决定采用 React 18"          → msg_type="decision"  compression_exempt=True  ✅ 永久保留
"```python\ndef foo(): ..."   → msg_type="code"       compression_exempt=True  ✅ 永久保留
"Error: ECONNREFUSED"        → msg_type="error"      compression_exempt=True  ✅ 永久保留
"好的，明白了"               → msg_type="chitchat"   tfidf_score=2.1          可被压缩
```

`compression_exempt=True` 的消息在 DAG 压缩时跳过 LLM 摘要，原文永久保留在上下文中。

### DAG 结构

```
原始消息 seq 1..N
     ↓  (叶子压缩，每块 ≤ 20K tokens)
  leaf_A   leaf_B   leaf_C   [fresh tail: 最后 32 条原始消息]
     ↓  (层级聚合)
  condensed_1     condensed_2
     ↓
  root_summary
```

每一层都可通过 `lobster_expand` 展开到原始消息，DAG 节点只追加、不修改，天然可追溯。

---

## Agent 工具集成

LobsterPress 提供三个工具供 Agent 在对话中主动调用：

```bash
# 全文搜索历史（FTS5，毫秒级响应）
python -m src.agent_tools grep "PostgreSQL" --db memory.db --conversation conv_123

# 查看 DAG 摘要结构
python -m src.agent_tools describe --db memory.db --conversation conv_123

# 展开摘要到原始消息
python -m src.agent_tools expand sum_abc123 --db memory.db --max-depth 2
```

Python API：

```python
from src.agent_tools import lobster_grep, lobster_describe, lobster_expand

# 搜索，按相关性排序
results = lobster_grep(db, "数据库选型", conversation_id="conv_123", limit=5)

# 查看摘要层级结构
structure = lobster_describe(db, conversation_id="conv_123")
# → {"total_summaries": 12, "max_depth": 3, "by_depth": {...}}

# 展开摘要，还原原始消息
detail = lobster_expand(db, "sum_abc123")
# → {"total_messages": 47, "messages": [...]}
```

---

## 配置参数

```python
manager = IncrementalCompressor(
    db,
    max_context_tokens=200_000,  # 目标模型上下文窗口（Claude=200K，GPT-4o=128K，Gemini=1M）
    context_threshold=0.75,      # 触发 DAG 压缩的使用率阈值
    fresh_tail_count=32,         # 受保护的最近消息数，不参与压缩
    leaf_chunk_tokens=20_000,    # 叶子摘要的源 token 上限
)
```

| 参数 | 默认值 | 说明 |
|---|---|---|
| `max_context_tokens` | 128,000 | 目标模型的上下文窗口大小，**必须按模型设置** |
| `context_threshold` | 0.75 | 触发 DAG 压缩的使用率阈值（0.0–1.0） |
| `fresh_tail_count` | 32 | 受保护的最近消息数，不参与任何压缩 |
| `leaf_chunk_tokens` | 20,000 | 叶子压缩分块大小（影响摘要粒度） |

---

## 数据迁移

从旧版本（v1.5.5）或其他格式批量导入：

```bash
# 从 JSON 导入（自动评分 + 分类）
python -m src.pipeline.batch_importer data.json --db memory.db

# 从 CSV 导入
python -m src.pipeline.batch_importer data.csv --format csv --db memory.db

# 指定批大小
python -m src.pipeline.batch_importer data.json --db memory.db --batch-size 50
```

---

## 项目结构

```
src/
├── database.py               # SQLite 存储层（消息、摘要、DAG 关系、FTS5 索引）
├── dag_compressor.py         # DAG 压缩引擎（叶子摘要 + 层级聚合）
├── agent_tools.py            # lobster_grep / lobster_describe / lobster_expand
├── incremental_compressor.py # 三层压缩调度器（项目主入口）
└── pipeline/
    ├── tfidf_scorer.py       # TF-IDF 评分 + 消息类型自动分类
    ├── semantic_dedup.py     # 余弦相似度去重（light 策略）
    └── batch_importer.py     # 历史数据批量导入工具
```

---

## 已知问题（v2.5.0）

> 以下问题正在 [Issue #95](https://github.com/SonicBotMan/lobster-press/issues/95) 跟踪，计划在 v2.5.1 修复

- **[高危]** FTS5 在消息更新时产生孤悬索引，导致搜索返回幽灵结果
- **[高危]** `light` 去重策略实际是空操作，TODO 未完成，三档策略只有两档生效
- **[中]** `max_context_tokens` 历史默认值硬编码为 128K，Claude/Gemini 用户需显式传入
- **[中]** `TFIDFScorer` 实例状态在多线程并发下不安全

---

## 版本历史

| 版本 | 日期 | 亮点 |
|---|---|---|
| **v2.5.0** ⭐ | 2026-03-17 | TF-IDF 评分、三层压缩、compression_exempt、BatchImporter |
| v2.0.0-alpha | 2026-03-15 | 无损 DAG 架构、FTS5 搜索、Agent 工具集 |
| v1.5.5 | 2026-03-13 | 有损批量压缩、6.67x 多线程加速 |

---

## 致谢

- **[lossless-claw](https://github.com/martian-engineering/lossless-claw)**（Martian Engineering）— DAG 压缩架构参考
- **[LCM 论文](https://papers.voltropy.com/LCM)**（Voltropy）— 无损上下文管理理论基础
- **罡哥（sonicman0261）** — 项目发起人和指导

---

## 许可证

[MIT License](LICENSE)

---

<div align="center">

如果觉得有用，请给个 ⭐ Star 支持一下！

![Star History Chart](https://api.star-history.com/svg?repos=SonicBotMan/lobster-press&type=Date)

Made with 💕 by SonicBotMan

</div>
