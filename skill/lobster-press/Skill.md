---
name: lobster-press
description: LobsterPress 认知记忆系统 - DAG 压缩 + OpenClaw ContextEngine + MCP 服务器，让 AI 拥有长期记忆和智能压缩能力
---

# LobsterPress - OpenClaw 认知记忆系统

## 概述

LobsterPress 是一个为 OpenClaw 设计的**认知记忆系统**，通过 DAG（有向无环图）压缩、遗忘曲线和语义记忆技术，实现智能上下文管理。

**最新版本**: v3.4.0 (2026-03-19)

**核心特性：**
- **DAG 压缩** - 有向无环图结构，保留语义关系
- **ContextEngine 集成** - 自动监测上下文使用率，智能触发压缩
- **MCP 服务器** - 通过 MCP 协议提供工具调用
- **认知记忆** - EM-LLM + HiMem + 遗忘曲线
- **真实压缩** - 返回真实的 token 数，不做估算

## 使用场景

当用户提到以下关键词时自动触发：
- "压缩会话"、"压缩上下文"
- "Token 不够了"、"上下文太长"
- "会话压缩"、"智能压缩"
- "清理对话"、"优化上下文"
- "记忆管理"、"长期记忆"

## 快速开始

### 安装依赖

```bash
cd ~/.openclaw/workspace/skills/lobster-press
pip install -r requirements.txt

# 可选：高精度 token 计数
pip install tiktoken
```

### 基本用法

**方式 1：MCP 工具调用（推荐）**

```json
{
  "name": "lobster_compress",
  "arguments": {
    "conversation_id": "current-session",
    "current_tokens": 100000,
    "token_budget": 128000,
    "force": false
  }
}
```

**方式 2：OpenClaw ContextEngine（自动）**

配置后，LobsterPress 会自动监测和压缩：

```json
// ~/.openclaw/openclaw.json
{
  "agents": {
    "defaults": {
      "plugins": {
        "slots": {
          "contextEngine": "lobster-press"
        }
      }
    }
  },
  "plugins": {
    "lobster-press": {
      "path": "@sonicbotman/lobster-press",
      "config": {
        "contextThreshold": 0.75,
        "strategy": "medium",
        "tokenBudget": 128000
      }
    }
  }
}
```

**方式 3：命令行（遗留）**

```bash
# 压缩当前会话
python3 scripts/context-compressor-v5.sh --session-id abc123

# 查看压缩预览
python3 scripts/context-compressor-v5.sh --dry-run abc123
```

## MCP 工具 API

### 核心工具

| 工具名称 | 功能 | 版本 |
|---------|------|------|
| `lobster_compress` | 自动上下文压缩（真实 DAG） | v3.3.0+ |
| `compress_session` | 会话压缩（真实 DAG） | v3.3.1+ |
| `preview_compression` | 预览压缩效果 | v3.2.0+ |
| `lobster_grep` | 全文搜索历史对话 | v3.2.2+ |
| `lobster_describe` | 查看 DAG 摘要结构 | v3.2.2+ |
| `lobster_expand` | 展开摘要节点 | v3.2.2+ |

### `lobster_compress` 参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `conversation_id` | string | 是 | 对话 ID |
| `current_tokens` | integer | 是 | 当前 token 数量 |
| `token_budget` | integer | 是 | token 预算 |
| `force` | boolean | 否 | 是否强制压缩（默认 false） |

**返回值**：

```json
{
  "compressed": true,
  "conversation_id": "abc123",
  "tokens_before": 100000,
  "tokens_after": 60000,
  "tokens_saved": 40000,
  "token_budget": 128000,
  "attempt": 1
}
```

## 压缩策略

| 策略 | 阈值 | 说明 |
|------|------|------|
| `light` | 90% | 轻度压缩，保留更多上下文 |
| `medium` | 75% | 中度压缩，平衡保留与压缩 |
| `aggressive` | 50% | 激进压缩，最大化节省 token |

## 架构设计

### DAG 压缩流程

```
┌─────────────────────────────────────────────────────────────┐
│                  OpenClaw Context Pipeline                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User Message → AI Response → afterTurn() Hook             │
│                                    │                        │
│                                    ↓                        │
│                          LobsterPress ContextEngine        │
│                                    │                        │
│                      ┌─────────────┴─────────────┐        │
│                      │                           │        │
│                Usage < 75%                 Usage >= 75%   │
│                      │                           │        │
│                      ↓                           ↓        │
│                   无操作                    compact()      │
│                                                │           │
│                                                ↓           │
│                                      DAGCompressor         │
│                                      (真实 DAG 压缩)        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 认知记忆系统

- **EM-LLM**：基于 LLM 的记忆编码
- **HiMem**：层次化记忆管理
- **遗忘曲线**：基于时间的重要性衰减

## 性能基准

| 上下文大小 | 原始 tokens | 压缩后 tokens | 压缩率 |
|-----------|------------|--------------|--------|
| 5k tokens | 5,000 | 2,000 | 60% |
| 15k tokens | 15,000 | 5,000 | 67% |
| 30k tokens | 30,000 | 8,000 | 73% |

## 目录结构

```
lobster-press/
├── skill/lobster-press/Skill.md   # 本文件
├── src/                           # 源代码
│   ├── database.py                # LobsterDatabase（18 张表 + FTS）
│   ├── dag_compressor.py          # DAG 压缩器
│   ├── semantic_memory.py         # 语义记忆层
│   ├── incremental_compressor.py  # 增量压缩
│   ├── event_segmenter.py         # 事件边界分割
│   └── pipeline/                  # 数据管道
├── mcp_server/                    # MCP 服务器
│   └── lobster_mcp_server.py      # MCP 工具实现
├── index.ts                       # OpenClaw ContextEngine
├── docs/                          # 文档
│   ├── API.md                     # API 文档
│   ├── ARCHITECTURE.md            # 架构文档
│   ├── OPENCLAW-INTEGRATION.md    # 集成指南
│   └── EXAMPLES.md                # 使用示例
└── tests/                         # 测试
    └── unit/test_context_engine.py
```

## 配置选项

在 `~/.openclaw/openclaw.json` 中配置：

```json
{
  "plugins": {
    "lobster-press": {
      "config": {
        "dbPath": "~/.openclaw/lobster.db",
        "llmProvider": "deepseek",
        "contextThreshold": 0.75,
        "strategy": "medium",
        "tokenBudget": 128000
      }
    }
  }
}
```

## 示例

### 示例 1：自动压缩（推荐）

配置 ContextEngine 后，LobsterPress 会自动监测和压缩：

```
# 用户正常对话
用户: 请帮我写一个 Python 脚本...
AI: 好的，我来帮你...

# LobsterPress 自动工作（后台）
[lobster-press] Context 78.5% > 75%, triggering auto-compress
[lobster-press] Compressed: 100000 → 60000 tokens (saved 40000)
```

### 示例 2：手动触发压缩

```json
{
  "name": "lobster_compress",
  "arguments": {
    "conversation_id": "current-session",
    "current_tokens": 100000,
    "token_budget": 128000,
    "force": true
  }
}
```

### 示例 3：预览压缩效果

```json
{
  "name": "preview_compression",
  "arguments": {
    "session_id": "abc123",
    "strategy": "medium"
  }
}
```

**返回**：

```json
{
  "status": "preview",
  "session_id": "abc123",
  "strategy": "medium",
  "message_count": 150,
  "estimated_tokens": 45000,
  "dry_run": true,
  "note": "No compression performed. Call without dry_run=True to compress."
}
```

## 依赖说明

**Python 版本**：3.8+

**核心依赖**：
- numpy >= 1.20.0
- scikit-learn >= 0.24.0

**可选依赖**：
- tiktoken >= 0.5.0（高精度 token 计数）
- openai >= 1.0.0（LLM 摘要，可选）

安装：
```bash
pip install -r requirements.txt

# 可选：高精度 token 计数
pip install tiktoken
```

## 版本历史

### v3.4.0 (2026-03-19)
- 修复 Issue #124 的三个 bug
- 修复双重阈值冲突
- 修复 dry_run 被忽略
- 修复 tokensAfter 假值

### v3.3.0 (2026-03-19)
- 实现 OpenClaw ContextEngine 接口
- 自动上下文监测与压缩
- 真实 DAG 压缩

### v3.2.0 (2026-03-19)
- MCP 服务器
- 认知记忆系统
- DAG 压缩器

完整更新日志: [CHANGELOG.md](../CHANGELOG.md)

## 常见问题

**Q: 压缩会丢失重要信息吗？**
A: 不会。DAG 压缩保留语义关系，可以通过 `lobster_expand` 还原原始消息。

**Q: ContextEngine 会自动压缩吗？**
A: 是的。当上下文使用率超过配置的阈值（默认 75%）时，会自动触发压缩。

**Q: 压缩后能省多少 token？**
A: 根据会话长度，压缩率从 60% 到 73% 不等。

**Q: tiktoken 是必需的吗？**
A: 不是。tiktoken 是可选依赖，未安装时会使用近似计算。

## 技术支持

- GitHub: https://github.com/SonicBotMan/lobster-press
- Issues: https://github.com/SonicBotMan/lobster-press/issues
- npm: https://www.npmjs.com/package/@sonicbotman/lobster-press
- 文档: docs/ 目录

---

**License**: MIT
**Version**: v3.4.0
**Author**: LobsterPress Team
**Maintainer**: 小云 (OpenClaw AI Agent)
