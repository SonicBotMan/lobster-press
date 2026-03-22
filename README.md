<div align="center">

<img src="assets/lobster-press-banner.png" alt="LobsterPress - 让AI的每一次对话，从'阅后即焚的幻影'进化为'数字海马体中的永久养分'" width="100%">

# 🧠 LobsterPress v4.0.28「深海」

**Cognitive Memory System for AI Agents**
*基于认知科学的 LLM 永久记忆引擎*

[![npm version](https://img.shields.io/npm/v/@sonicbotman/lobster-press.svg)](https://www.npmjs.com/package/@sonicbotman/lobster-press)
[![GitHub release](https://img.shields.io/github/release/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press/releases)
[![Test](https://github.com/SonicBotMan/lobster-press/workflows/Test/badge.svg)](https://github.com/SonicBotMan/lobster-press/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)

**中文** | [English](README_EN.md)

**最新版本**: [v4.0.28](https://github.com/SonicBotMan/lobster-press/releases/tag/v4.0.28) · [更新日志](CHANGELOG.md)

</div>

---

## 🎯 核心价值

**问题**：所有 LLM 都受限于上下文窗口。传统方案用滑动窗口截断——旧对话被永久丢弃，AI 陷入"失忆"循环。

**解决方案**：LobsterPress 基于认知科学实现 **DAG 无损压缩 + 遗忘曲线 + 语义记忆**，让 AI Agent 拥有类似人类的记忆系统：

- ✅ **无损压缩**：100% 原始消息可追溯
- ✅ **智能遗忘**：关键决策永久保留，闲聊自动衰减
- ✅ **知识提取**：从对话中自动提取结构化知识
- ✅ **矛盾检测**：自动发现和更新冲突知识
- ✅ **自动触发**：三种策略（定时/紧急/被动）自动压缩

---

## 📦 安装

### 系统要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| **OpenClaw Gateway** | 2026.3.9+ | 推荐，支持 afterTurn 钩子 |
| **Node.js** | 18+ | OpenClaw 插件模式 |
| **Python** | 3.10+ | MCP Server 运行时 |

> ⚠️ **重要**: 作为 OpenClaw 插件时，**必须全局安装**才能被发现。

### OpenClaw 插件安装（推荐）

```bash
# 全局安装
npm install -g @sonicbotman/lobster-press

# 验证安装
lobster-press --version
```

### 配置示例

```json
{
  "plugins": {
    "entries": {
      "lobster-press": {
        "enabled": true,
        "config": {
          "llmProvider": "deepseek",
          "llmModel": "deepseek-chat",
          "llmApiKey": "${LOBSTER_LLM_API_KEY}",
          "contextThreshold": 0.8,
          "freshTailCount": 32,
          "namespace": "default"
        }
      }
    }
  }
}
```

### 独立使用（Python）

```bash
pip install -e .

# 运行 MCP Server
python -m mcp_server.lobster_mcp_server --db ~/.openclaw/lobster.db
```

---

## 🏗️ 架构概述

### 五大模块（v4.0「深海」）

```
┌─────────────────────────────────────────────────────────────┐
│                    LobsterPress v4.0                        │
├─────────────────────────────────────────────────────────────┤
│  模块一: CMV 三遍无损压缩                                    │
│  ├── Pass 1: 剥离 base64/长 JSON 冗余                       │
│  ├── Pass 2: 去重工具结果                                   │
│  └── Pass 3: 折叠系统样板代码                               │
├─────────────────────────────────────────────────────────────┤
│  模块二: C-HLR+ 自适应遗忘曲线                               │
│  └── h = base_h × (1 + α × complexity) × spaced_bonus       │
├─────────────────────────────────────────────────────────────┤
│  模块三: Focus 主动压缩触发                                  │
│  ├── 定时触发: 每 12 轮                                     │
│  ├── 紧急触发: 上下文 > 85%                                 │
│  └── 被动触发: 上下文 > 80%                                 │
├─────────────────────────────────────────────────────────────┤
│  模块四: R³Mem 可逆三层压缩                                  │
│  ├── Layer 1: Document-Level (返回子摘要)                   │
│  ├── Layer 2: Paragraph-Level (返回原始消息)                │
│  └── Layer 3: Entity-Level (按实体过滤)                     │
├─────────────────────────────────────────────────────────────┤
│  模块五: WMR 工具框架                                        │
│  ├── Write: compact, correct                                │
│  ├── Manage: sweep, assemble, prune                         │
│  └── Read: grep, describe, expand, status                   │
└─────────────────────────────────────────────────────────────┘
```

### ContextEngine 集成

LobsterPress 实现了完整的 OpenClaw ContextEngine 接口：

| 方法 | 触发时机 | 功能 |
|------|----------|------|
| `prepareContext` | 每轮对话开始前 | 注入最新摘要到 system prompt |
| `afterTurn` | 每轮对话结束后 | 检查上下文使用率，自动触发压缩 |
| `compact` | 手动调用 | 强制执行 DAG 压缩 |
| `assemble` | 上下文组装时 | 按三层记忆模型拼装最优上下文 |

---

## 🛠️ MCP 工具列表

### Read 层（读取记忆）

| 工具 | 说明 | 必需参数 |
|------|------|----------|
| `lobster_grep` | 全文搜索（FTS5 + TF-IDF） | `query` |
| `lobster_describe` | 查看 DAG 摘要结构 | `conversation_id` 或 `summary_id` |
| `lobster_expand` | 展开摘要到原始消息 | `summary_id` |
| `lobster_status` | 系统健康报告 | - |

### Write 层（写入记忆）

| 工具 | 说明 | 必需参数 |
|------|------|----------|
| `lobster_compress` | 触发 DAG 压缩 | `conversation_id` |
| `lobster_correct` | 纠错记忆内容 | `target_type`, `target_id`, `correction_type` |

### Manage 层（管理记忆）

| 工具 | 说明 | 必需参数 |
|------|------|----------|
| `lobster_sweep` | 标记衰减消息 | `conversation_id` |
| `lobster_assemble` | 拼装三层上下文 | `conversation_id` |
| `lobster_prune` | 删除 decayed 消息 | `conversation_id` |

### 调试工具

| 工具 | 说明 |
|------|------|
| `lobster_check_context` | 手动检查上下文（降级方案） |

---

## 🚀 快速上手

### Python API

```python
from src.database import LobsterDatabase
from src.dag_compressor import DAGCompressor
from src.incremental_compressor import IncrementalCompressor

# 初始化
db = LobsterDatabase("~/.openclaw/lobster.db")
compressor = DAGCompressor(db)
manager = IncrementalCompressor(
    db,
    max_context_tokens=200_000,
    context_threshold=0.8,
    fresh_tail_count=32
)

# 新消息触发压缩检查
result = manager.on_new_message("conv_123", {
    "id": "msg_001",
    "role": "user",
    "content": "我们决定用 PostgreSQL 作为主数据库",
    "timestamp": "2026-03-21T10:00:00Z"
})

print(result["compression_strategy"])  # "none" | "light" | "aggressive"
```

### Agent 工具调用

```python
from src.agent_tools import lobster_grep, lobster_describe, lobster_expand

# 搜索历史
results = lobster_grep(db, "PostgreSQL", conversation_id="conv_123", limit=5)

# 查看摘要结构
structure = lobster_describe(db, conversation_id="conv_123")
# → {"total_summaries": 12, "max_depth": 3, "by_depth": {...}}

# 展开摘要
messages = lobster_expand(db, "sum_abc123", max_depth=2)
# → {"total_messages": 47, "messages": [...]}
```

---

## 📚 学术基础

| 论文/理论 | 应用 |
|-----------|------|
| **EM-LLM (ICLR 2025)** | 事件分割、语义边界检测 |
| **HiMem** | DAG 压缩、三级摘要结构 |
| **Ebbinghaus Forgetting Curve** | 动态遗忘：R(t) = base × e^(-t/stability) |
| **Memory Reconsolidation (Nader, 2000)** | 矛盾检测、知识重巩固 |
| **CMV** | 三遍无损压缩 |
| **C-HLR+ (arXiv:2004.11327)** | 复杂度驱动半衰期 |
| **Focus (arXiv:2502.15957)** | 主动压缩触发 |
| **R³Mem (arXiv:2502.15957)** | 可逆三层压缩 |

---

## ⚙️ 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_context_tokens` | 128,000 | 目标模型上下文窗口 |
| `context_threshold` | 0.8 | 触发压缩的使用率阈值 |
| `fresh_tail_count` | 32 | 受保护的最近消息数 |
| `leaf_chunk_tokens` | 20,000 | 叶子压缩分块大小 |
| `focus_interval` | 12 | Focus 定时触发间隔（轮） |
| `urgent_threshold` | 0.85 | Focus 紧急触发阈值 |

---

## 🤖 LLM 提供商

支持 8 个主流提供商，用于高质量摘要生成：

**国际**：OpenAI, Anthropic, Google, Mistral

**国内**：DeepSeek ⭐, 智谱 GLM ⭐, 百度文心, 阿里通义

```bash
# 环境变量配置
export LOBSTER_LLM_PROVIDER=deepseek
export LOBSTER_LLM_API_KEY=sk-xxx
export LOBSTER_LLM_MODEL=deepseek-chat
```

---

## 📊 压缩策略

```
上下文使用率        策略              LLM 成本
─────────────────────────────────────────────────
< 60%              无操作            $0
60% – 80%          语义去重          $0
> 80%              DAG 摘要压缩      $
```

**无损原则**：user/assistant 消息永不修改，仅 trim 工具输出。

---

## 🗂️ 项目结构

```
├── index.ts                    # OpenClaw 插件入口（ContextEngine）
├── openclaw.plugin.json        # 插件配置
├── mcp_server/
│   └── lobster_mcp_server.py   # MCP Server（14 个工具）
└── src/
    ├── database.py             # SQLite 存储层
    ├── dag_compressor.py       # DAG 压缩引擎
    ├── incremental_compressor.py  # 三层压缩调度器
    ├── three_pass_trimmer.py   # CMV 三遍无损压缩
    ├── semantic_memory.py      # 语义记忆层
    ├── llm_client.py           # LLM 客户端
    ├── llm_providers.py        # 8 个提供商适配
    ├── prompts.py              # Prompt 模板
    ├── agent_tools.py          # Python API
    └── pipeline/
        ├── tfidf_scorer.py     # TF-IDF 评分
        ├── semantic_dedup.py   # 语义去重
        └── ...
```

---

## 📜 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| **v4.0.28** ⭐ | 2026-03-22 | Issue #167 审计修复（5 个 Bug） |
| **v4.0.25** | 2026-03-21 | Issue #154 修复（ESM 兼容 + 截断逻辑） |
| **v4.0.25** | 2026-03-21 | Issue #153 修复（per-session 锁 + 版本动态） |
| **v4.0.25** | 2026-03-21 | README 重写 + 学术引用 |
| v4.0.25 | 2026-03-20 | 安全修复（CodeQL） |
| v4.0.25 | 2026-03-19 | 五大模块重构 |
| v4.0.25 | 2026-03-19 | Bug 修复（7 个） |
| v4.0.25 | 2026-03-19 | MemOS 架构 |
| v4.0.25 | 2026-03-19 | ContextEngine 集成 |
| v4.0.25 | 2026-03-17 | LLM 多提供商 |
| v4.0.25 | 2026-03-17 | 认知科学重构 |
| v4.0.25 | 2026-03-13 | 初始发布 |

详见 [CHANGELOG.md](CHANGELOG.md)

---

## 🙏 致谢

### 学术引用

如果 LobsterPress 对你的研究有帮助，请引用以下论文：

```bibtex
@inproceedings{emllm2025,
  title={EM-LLM: Event-Based Memory Management for Large Language Models},
  booktitle={ICLR 2025},
  year={2025}
}

@article{nader2000memory,
  title={Memory reconsolidation: An update},
  author={Nader, Karim and Schafe, Glenn E and Le Doux, Joseph E},
  journal={Nature},
  year={2000}
}

@article{ebbinghaus1885memory,
  title={Memory: A contribution to experimental psychology},
  author={Ebbinghaus, Hermann},
  journal={Teachers College, Columbia University},
  year={1885}
}

@article{chlr2020,
  title={C-HLR: Continual Hebbian Learning with Replay},
  author={Parisi, German I and Tani, Jun and Weber, Cornelius and Wermter, Stefan},
  journal={arXiv preprint arXiv:2004.11327},
  year={2020}
}

@article{focus2025,
  title={Focus: Attention-based Context Compression for LLMs},
  journal={arXiv preprint arXiv:2502.15957},
  year={2025}
}

@article{r3mem2025,
  title={R³Mem: Reversible Residual Recurrent Memory for Long-context LLMs},
  journal={arXiv preprint arXiv:2502.15957},
  year={2025}
}

@article{cmv2024,
  title={Context Maintenance and Retrieval for Efficient LLM Inference},
  journal={arXiv preprint},
  year={2024}
}

@inproceedings{himem2024,
  title={HiMem: Hierarchical Memory Management for Long-context LLMs},
  booktitle={NeurIPS 2024},
  year={2024}
}
```

### 开源项目

- **[lossless-claw](https://github.com/martian-engineering/lossless-claw)** — DAG 压缩架构参考
- **[OpenClaw](https://github.com/openclaw/openclaw)** — 插件平台

---

<div align="center">

**如果 LobsterPress 对你的项目有帮助，请给个 ⭐ Star！**

**Made with 🧠 by SonicBotMan & Xiao Yun**

*基于认知科学，为 AI Agent 构建人类般的记忆系统*

</div>
