<div align="center">

<img src="assets/lobster-press-banner.png" alt="LobsterPress - 让AI的每一次对话，从'阅后即焚的幻影'进化为'数字海马体中的永久养分'" width="100%">

# 🧠 LobsterPress v5.0.0「MemOS 4-Phase」

**Cognitive Memory System for AI Agents**
*基于认知科学的 LLM 永久记忆引擎*

[![npm version](https://img.shields.io/npm/v/@sonicbotman/lobster-press.svg)](https://www.npmjs.com/package/@sonicbotman/lobster-press)
[![GitHub release](https://img.shields.io/github/release/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press/releases)
[![Test](https://github.com/SonicBotMan/lobster-press/workflows/Test/badge.svg)](https://github.com/SonicBotMan/lobster-press/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)

**中文** | [English](README_EN.md)

**最新版本**: [v5.0.0](https://github.com/SonicBotMan/lobster-press/releases/tag/v5.0.0) · [更新日志](CHANGELOG.md)

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

## 📦 安装教程（面向 OpenClaw 用户）

### 前置条件

在安装 LobsterPress 之前，请确保您的系统满足以下要求：

| 依赖 | 版本 | 如何检查 | 如何安装 |
|------|------|----------|----------|
| **OpenClaw Gateway** | 2026.3.9+ | `openclaw gateway version` | [安装指南](https://docs.openclaw.ai) |
| **Node.js** | 18+ | `node --version` | [下载地址](https://nodejs.org) |
| **Python** | 3.10+ | `python3 --version` | 系统自带或 [下载](https://python.org) |
| **npm** | 9+ | `npm --version` | 随 Node.js 安装 |

> 💡 **提示**: 如果您已经在使用 OpenClaw，那么 Node.js 和 Python 应该已经安装好了。

---

### 安装步骤（推荐方式）

> ⚠️ **重要**: LobsterPress 是 OpenClaw 插件，必须安装到 `~/.openclaw/extensions/lobster-press/` 目录才能工作。**不要**使用 `npm install -g`（全局安装不会让 OpenClaw 加载插件）。

#### 步骤 1: 创建插件目录

```bash
# 创建 OpenClaw 插件目录
mkdir -p ~/.openclaw/extensions/lobster-press
```

#### 步骤 2: 安装 LobsterPress

**方式 A: 从 npm 下载并安装（推荐）**

```bash
# 进入插件目录
cd ~/.openclaw/extensions/lobster-press

# 下载最新版本 tarball
npm pack @sonicbotman/lobster-press@latest

# 解压到当前目录
tar -xzf *.tgz --strip-components=1

# 清理 tarball 文件
rm *.tgz
```

**方式 B: 从 GitHub Release 下载（离线安装）**

1. 访问 [GitHub Releases](https://github.com/SonicBotMan/lobster-press/releases)
2. 下载最新版本的 `lobster-press-X.X.X.tgz`
3. 解压到插件目录：

```bash
cd ~/.openclaw/extensions/lobster-press
tar -xzf /path/to/lobster-press-X.X.X.tgz --strip-components=1
```

#### 步骤 3: 验证安装

```bash
# 检查插件文件是否存在
ls ~/.openclaw/extensions/lobster-press/

# 预期输出: dist/  mcp_server/  openclaw.plugin.json  package.json  README.md  src/
```

#### 步骤 4: 配置 LobsterPress

**方式 1: 使用 AI 助手引导配置（推荐）**

在与 AI 对话时，直接说：

```
帮我配置 LobsterPress 记忆系统
```

AI 会自动调用 `lobster_configure` 工具，引导您完成配置。

**方式 2: 手动配置（高级用户）**

编辑 `~/.openclaw/openclaw.json`，添加插件配置：

```json
{
  "plugins": {
    "allow": ["lobster-press"],
    "entries": {
      "lobster-press": {
        "enabled": true
      }
    },
    "slots": {
      "contextEngine": "lobster-press"
    }
  }
}
```

> ⚠️ **重要**: 推荐使用方式 1（AI 引导配置），避免配置错误。

#### 步骤 5: 重启 OpenClaw Gateway

```bash
# 方式 1: 使用 openclaw 命令（如果可用）
openclaw gateway restart

# 方式 2: 使用 systemctl
systemctl --user restart openclaw-gateway

# 方式 3: 发送重启信号
kill -HUP $(pgrep openclaw-gateway)
```

#### 步骤 6: 验证 LobsterPress 是否工作

在与 AI 对话时，说：

```
我喜欢吃苹果
```

然后过几轮对话后，问：

```
我刚才说我喜欢吃什么？
```

如果 AI 能回答"苹果"，说明 LobsterPress 记忆系统已经正常工作！

---

### 快速验证命令

安装完成后，可以使用以下命令快速验证：

```bash
# 1. 检查插件文件
ls ~/.openclaw/extensions/lobster-press/

# 2. 检查 OpenClaw 配置
cat ~/.openclaw/openclaw.json | grep -A 5 "lobster-press"

# 3. 检查 Gateway 日志（确认插件加载）
journalctl --user -u openclaw-gateway -f | grep lobster
```

---

### 配置向导使用指南

LobsterPress v5.0.0 提供了 5 步交互式配置向导：

| 步骤 | 说明 | 您需要做的 |
|------|------|-----------|
| **1. 欢迎** | 介绍配置流程 | 阅读说明 |
| **2. LLM 选择** | 选择使用 LLM 还是 TF-IDF | 选择是否使用 LLM |
| **3. Provider** | 选择 LLM 提供商 | 选择 OpenAI/智谱/DeepSeek 等 |
| **4. API Key** | 输入 API Key | 输入您的 API Key |
| **5. 完成** | 确认配置 | 查看配置示例 |

**配置示例对话**：

```
您: 帮我配置 LobsterPress

AI: 欢迎使用 LobsterPress 配置向导！🦞
    LobsterPress 是一个基于认知科学的 LLM 永久记忆引擎。
    
    **第一步：选择记忆模式**
    
    LobsterPress 支持两种记忆模式：
    1. **LLM 模式**（推荐）：使用大语言模型智能提取记忆
    2. **TF-IDF 模式**：基于词频统计的传统模式
    
    请选择您想使用的模式（LLM/TF-IDF）：

您: LLM

AI: ✅ 已选择 LLM 模式
    
    **第二步：选择 LLM Provider**
    
    请选择您的 LLM 提供商：
    1. OpenAI
    2. Anthropic
    3. 智谱 AI（GLM）
    4. DeepSeek
    5. 自定义
    
    请输入选项（1-5）：

您: 3

AI: ✅ 已选择智谱 AI
    
    **第三步：输入 API Key**
    
    请输入您的智谱 AI API Key：
    （格式：xxxxxxxx.xxxxxxxxxxxxxxxx）
    
    ⚠️ 安全提示：API Key 会被加密存储，不会上传到云端。

您: [您的 API Key]

AI: ✅ 配置完成！
    
    LobsterPress 已经配置好了，您的 AI 助手现在拥有了长期记忆能力！
    
    **配置摘要**：
    - 记忆模式: LLM
    - Provider: 智谱 AI
    - API Key: 已配置 ✅
    
    **下一步**：重启 OpenClaw Gateway 使配置生效。
```

---

### 常见问题（FAQ）

#### Q1: 安装后 AI 还是记不住之前说的话？

**可能原因**：
1. OpenClaw Gateway 没有重启
2. 配置文件中没有启用 `lobster-press`
3. `slots.contextEngine` 没有设置

**解决方法**：
```bash
# 1. 检查配置
cat ~/.openclaw/openclaw.json | grep -A 5 "lobster-press"

# 2. 重启 Gateway
systemctl --user restart openclaw-gateway

# 3. 查看日志
journalctl --user -u openclaw-gateway -f | grep lobster
```

#### Q2: 提示 "lobster-press command not found"？

**可能原因**：npm 全局安装路径不在 PATH 中。

**解决方法**：
```bash
# 检查 npm 全局路径
npm config get prefix

# 添加到 PATH（以 bash 为例）
echo 'export PATH="$(npm config get prefix)/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### Q3: 配置后 Gateway 启动失败？

**可能原因**：配置文件 JSON 格式错误。

**解决方法**：
```bash
# 验证 JSON 格式
python3 -m json.tool ~/.openclaw/openclaw.json

# 如果报错，检查 JSON 语法（逗号、引号等）
# 或者恢复备份
cp ~/.openclaw/openclaw.json.backup ~/.openclaw/openclaw.json
```

#### Q4: 如何查看 LobsterPress 是否在运行？

**方法 1: 查看日志**
```bash
journalctl --user -u openclaw-gateway -f | grep -i lobster
```

**方法 2: 检查数据库**
```bash
# 查看是否有记忆被保存
sqlite3 ~/.openclaw/lobster.db "SELECT COUNT(*) FROM messages;"
```

#### Q5: 如何卸载 LobsterPress？

```bash
# 1. 移除配置
# 编辑 ~/.openclaw/openclaw.json，删除 "lobster-press" 相关配置

# 2. 卸载 npm 包
npm uninstall -g @sonicbotman/lobster-press

# 3. 删除数据库（可选）
rm ~/.openclaw/lobster.db

# 4. 重启 Gateway
systemctl --user restart openclaw-gateway
```

---

### 获取帮助

如果您遇到问题，可以通过以下方式获取帮助：

1. **查看文档**: [docs.openclaw.ai](https://docs.openclaw.ai)
2. **GitHub Issues**: [提交问题](https://github.com/SonicBotMan/lobster-press/issues)
3. **Discord 社区**: [加入讨论](https://discord.com/invite/clawd)

---

### 高级配置（可选）

如果您是高级用户，可以手动配置以下选项：

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
    },
    "slots": {
      "contextEngine": "lobster-press"
    }
  }
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `llmProvider` | LLM 提供商（openai/anthropic/zhipu/deepseek） | - |
| `llmModel` | LLM 模型名称 | - |
| `llmApiKey` | API Key（建议用环境变量） | - |
| `contextThreshold` | 上下文使用率阈值（触发压缩） | 0.8 |
| `freshTailCount` | 保留最近 N 条消息不压缩 | 32 |
| `namespace` | 命名空间（多租户隔离） | default |

> 💡 **安全提示**: API Key 建议使用环境变量，不要直接写在配置文件中：
> ```bash
> export LOBSTER_LLM_API_KEY="your-api-key"
> ```

---

## 🏗️ 架构概述

### MemOS 4-Phase 架构（v5.0）

```
┌─────────────────────────────────────────────────────────────┐
│                    LobsterPress v5.0「MemOS」                  │
├─────────────────────────────────────────────────────────────┤
│  Phase 1: Core Intelligence (向量嵌入 + RRF/MMR)           │
│  ├── Vector Embedder: OpenAI兼容API + numpy离线             │
│  ├── Hybrid Retriever: FTS5+Vector → RRF(k=60) → MMR     │
│  ├── LLM Fallback Chain: skill→summary→native→mock        │
│  └── Dual Decay: 12h压缩 / 14d检索                        │
├─────────────────────────────────────────────────────────────┤
│  Phase 2: Skill Evolution (技能进化)                       │
│  ├── Task Detector: 2h超时 + LLM话题判断                    │
│  ├── Skill Evolver: 规则过滤→LLM评估→SKILL.md→评分        │
│  └── MCP lobster_skill: get/install/list                    │
├─────────────────────────────────────────────────────────────┤
│  Phase 3: Multi-Agent (多智能体)                          │
│  ├── Owner字段: 消息/摘要/笔记按Agent隔离                   │
│  ├── Public Memory: lobster_memory_write_public              │
│  └── Skill Sharing: lobster_skill_search/publish             │
├─────────────────────────────────────────────────────────────┤
│  Phase 4: Engineering (工程化)                              │
│  ├── Viewer Web UI: 127.0.0.1 + SHA-256认证                 │
│  ├── Async Queue: 后台任务队列                             │
│  └── OpenClaw Migration: 🦐标识 + 断点续传                  │
├─────────────────────────────────────────────────────────────┤
│  Legacy: CMV三遍无损压缩 + C-HLR+遗忘曲线 + R³Mem三层      │
└─────────────────────────────────────────────────────────────┘
```

### Lifecycle Hooks 集成

LobsterPress 通过 OpenClaw lifecycle hooks 实现自动记忆管理：

| Hook | 触发时机 | 功能 | 状态 |
|------|----------|------|------|
| `before_agent_start` | 每轮对话开始前 | 自动注入历史记忆（按 semantic > episodic > working 优先级） | ✅ 启用 |
| `agent_end` | 每轮对话结束后 | 自动保存用户输入和 Agent 回复 | ✅ 启用 |

**手动工具**（可选）：
| 工具 | 触发时机 | 功能 | 状态 |
|------|----------|------|------|
| `lobster_compress` | 手动调用 | 强制执行 DAG 压缩 | ✅ 可用 |
| `lobster_assemble` | 手动调用 | 按三层记忆模型拼装最优上下文 | ✅ 可用 |

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

### v5.0 新工具 (Skill Evolution)

| 工具 | 说明 | 必需参数 |
|------|------|----------|
| `lobster_skill` | 查询/安装技能 | `action`, `skill_id/conversation_id` |

### v5.0 新工具 (Multi-Agent)

| 工具 | 说明 | 必需参数 |
|------|------|----------|
| `lobster_memory_write_public` | 写入公共记忆 | `content` |
| `lobster_skill_search` | 搜索技能(self/public/mix) | `query`, `scope` |
| `lobster_skill_publish` | 公开技能 | `skill_id` |
| `lobster_skill_unpublish` | 私有化技能 | `skill_id` |

### v5.0 新工具 (Engineering)

| 工具 | 说明 | 必需参数 |
|------|------|----------|
| `lobster_viewer` | 打开Web UI | `action`, `port` |
| `lobster_import` | 导入OpenClaw记忆 | `action` |

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

### v5.0 Python API

```python
# v5.0: Vector Embedder
from src.vector.embedder import create_embedder
embedder = create_embedder()  # 自动降级

# v5.0: Hybrid Retriever
from src.vector.retriever import HybridRetriever
retriever = HybridRetriever(db, embedder)
results = retriever.search("PostgreSQL", top_k=5)

# v5.0: Skill Evolution
from src.skills.task_detector import TaskDetector
from src.skills.evolver import SkillEvolver
detector = TaskDetector(db, llm_client)
tasks = detector.detect_tasks("conv_123")

evolver = SkillEvolver(db, llm_client)
skill_id = evolver.evaluate_and_generate(task, "conv_123")

# v5.0: Async Queue
from src.async_queue.worker import AsyncWorker
worker = AsyncWorker(db, embedder, llm_client)
worker.start()
worker.enqueue('embed', {'target_type': 'message', 'target_id': 'msg_xxx', 'content': '...'})

# v5.0: Viewer Web UI
from src.viewer.server import start_viewer
server = start_viewer(db, port=18799, password="mypassword")
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
| `embed_provider` | OpenAI兼容API | 向量嵌入提供商 |
| `embed_endpoint` | - | 嵌入API端点 |
| `embed_model` | bge-m3 | 嵌入模型 |
| `retrieval_half_life_days` | 14.0 | 检索衰减半衰期(天) |
| `compression_half_life_hours` | 12 | 压缩衰减半衰期(小时) |

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

# LLM Fallback Chain (v5.0)
export LOBSTER_LLM_SKILL_PROVIDER=openai     # 可选
export LOBSTER_LLM_SUMMARY_PROVIDER=openai   # 可选
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
│   └── lobster_mcp_server.py   # MCP Server（22 个工具）
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
    ├── vector/                  # v5.0: 向量嵌入
    │   ├── embedder.py         # OpenAI兼容 + numpy离线
    │   └── retriever.py        # RRF/MMR/Decay
    ├── skills/                 # v5.0: 技能进化
    │   ├── models.py          # Skill, TaskSummary
    │   ├── task_detector.py   # 2h超时 + LLM判断
    │   └── evolver.py         # 规则过滤→评分→SKILL.md
    ├── async_queue/            # v5.0: 异步队列
    │   └── worker.py          # 后台任务处理
    ├── viewer/                 # v5.0: Web UI
    │   └── server.py          # HTTP服务
    ├── migration/              # v5.0: OpenClaw迁移
    │   └── importer.py        # 🦐标识 + 断点续传
    └── pipeline/
        ├── tfidf_scorer.py     # TF-IDF 评分
        ├── semantic_dedup.py   # 语义去重
        └── ...
```

---

## 📜 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| **v5.0.0** ⭐ | 2026-04-05 | MemOS 4-Phase优化: 向量嵌入/技能进化/多智能体/工程化 |
| **v4.0.89** ⭐ | 2026-03-24 | 记忆优先级排序：semantic > episodic > working，长期记忆优先注入 |
| **v4.0.49** | 2026-03-23 | MCP 工具模式：禁用 lifecycle hooks，添加手动记忆管理指南 |
| **v4.0.41** | 2026-03-22 | Issue #174 专家反馈修复（6 个优化） |
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

@article{memos2026,
  title={MemOS: Memory Operating System for AI Agents},
  journal={https://memos-claw.openmem.net},
  year={2026}
}
```

### 开源项目

- **[lossless-claw](https://github.com/martian-engineering/lossless-claw)** — DAG 压缩架构参考
- **[OpenClaw](https://github.com/openclaw/openclaw)** — 插件平台

---

## 🌟 Star History

If this project helps you, please ⭐️ star it!

[![GitHub stars](https://img.shields.io/github/stars/SonicBotMan/lobster-press?style=for-the-badge&logo=github&color=yellow)](https://github.com/SonicBotMan/lobster-press/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/SonicBotMan/lobster-press?style=for-the-badge&logo=github&color=blue)](https://github.com/SonicBotMan/lobster-press/network/members)

<details>
<summary>📊 View Star History Chart</summary>

[![Star History Chart](https://api.star-history.com/svg?repos=SonicBotMan/lobster-press&type=Date)](https://star-history.com/#SonicBotMan/lobster-press&Date)

<i>Note: The chart above may take 24-48 hours to update due to GitHub's image cache. Click to view real-time data on Star History website.</i>

</details>


<div align="center">

**如果 LobsterPress 对你的项目有帮助，请给个 ⭐ Star！**

**Made with 🧠 by SonicBotMan & Xiao Yun**

*基于认知科学，为 AI Agent 构建人类般的记忆系统*

</div>
