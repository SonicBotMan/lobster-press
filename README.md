<div align="center">

<img src="assets/lobster-press-banner.png" alt="LobsterPress — 跑在本地的中文优先 AI Agent 记忆系统" width="100%">

# 🧠 LobsterPress

**Cognitive Memory System for AI Agents**
*本地优先的 LLM 永久记忆引擎：SQLite 单文件、零向量库依赖*

[![npm version](https://img.shields.io/npm/v/@sonicbotman/lobster-press.svg)](https://www.npmjs.com/package/@sonicbotman/lobster-press)
[![GitHub release](https://img.shields.io/github/release/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press/releases)
[![Test](https://github.com/SonicBotMan/lobster-press/workflows/Test/badge.svg)](https://github.com/SonicBotMan/lobster-press/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)

**中文** | [English](README_EN.md)

**当前版本**: [v5.1.1](https://github.com/SonicBotMan/lobster-press/releases) · [完整更新历史](CHANGELOG.md)

</div>

---

## 这是什么

所有 LLM 都受限于上下文窗口，滑动窗口截断会把旧对话永久丢弃。LobsterPress 把 Agent 的每轮对话存进本地 SQLite，用认知科学策略（DAG 无损压缩 + 遗忘曲线 + 语义笔记）自动管理记忆——原始消息永不删除，任何摘要都可回溯。

**定位一句话**：跑在本地的中文优先 Agent 记忆引擎。选它当你不想引入云依赖/向量数据库，且主力场景是中文。

## 核心能力

| 能力 | 说明 | 深读 |
|------|------|------|
| 🗜️ DAG 无损压缩 | 分层摘要削减上下文，原始消息 100% 可追溯 | [架构](docs/ARCHITECTURE.md) |
| ⏳ 遗忘曲线 | C-HLR+ 双半衰期：关键决策保留，闲聊自动衰减 | [架构](docs/ARCHITECTURE.md) |
| 📝 语义笔记 + 矛盾检测 | 从对话提取结构化知识，新主张与旧笔记冲突时自动发现 | [API](docs/API.md) |
| 🔍 中文全文检索 | FTS5 trigram 分词，≥3 字符走索引、短查询自动回退 LIKE | [API](docs/API.md) |
| 🧬 技能进化 | 把高频任务对话沉淀成可复用的 SKILL.md | [使用示例](docs/MANUAL_MEMORY.md) |
| 👥 多 Agent 隔离 | owner/namespace 双层隔离 + 公共记忆区 | [架构](docs/ARCHITECTURE.md) |

## 快速安装（OpenClaw 插件）

```bash
# 1. 创建插件目录（必须装这里，不要 npm install -g）
mkdir -p ~/.openclaw/extensions/lobster-press && cd $_
# 2. 下载解压
npm pack @sonicbotman/lobster-press@latest && tar -xzf *.tgz --strip-components=1 && rm *.tgz
# 3. 重启 Gateway 后说一句"帮我配置 LobsterPress"，AI 会引导完成 LLM 配置
```

前置：OpenClaw Gateway ≥ 2026.4.2、Node.js 18+、Python 3.10+。验证装好：对 Agent 说「用 lobster_status 报告系统状态」。
完整步骤 / 故障排查 → **[安装指南](docs/OPENCLAW-INTEGRATION.md)** · **[FAQ](docs/FAQ.md)**

## MCP 工具（17 个）

| 层 | 工具 |
|----|------|
| 读取 | `lobster_grep` 全文搜索 · `lobster_describe` 摘要结构 · `lobster_expand` 展开原始消息 · `lobster_status` 健康报告 |
| 写入 | `lobster_ingest` 消息入库 · `lobster_compress` 触发压缩 · `lobster_correct` 纠错 |
| 管理 | `lobster_assemble` 拼装上下文 · `lobster_sweep` 衰减标记 · `lobster_prune` 清理 |
| 技能/多Agent | `lobster_skill` · `lobster_skill_search` · `lobster_skill_publish` · `lobster_skill_unpublish` · `lobster_memory_write_public` |
| 工程 | `lobster_viewer` Web UI · `lobster_import` OpenClaw 迁移 |

参数与返回值详情 → [docs/API.md](docs/API.md)。OpenClaw 插件层另有 `lobster_configure` / `lobster_check_context` 两个 TS 工具。

## 和 mem0 / letta 怎么选

| | LobsterPress | mem0 | letta |
|---|---|---|---|
| 形态 | 本地嵌入式引擎（SQLite 单文件） | 托管向量记忆服务 | 有状态 Agent 运行时 |
| 中文检索 | ✅ trigram 原生 | 依赖 embedding | 依赖 embedding |
| 独有能力 | 技能进化 + 矛盾检测 | 生态成熟 | Agent 长期运行 |

核实日期 2026-09-01；详细对比与「什么时候别选我」→ [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 文档索引

| 文档 | 内容 |
|------|------|
| [docs/OPENCLAW-INTEGRATION.md](docs/OPENCLAW-INTEGRATION.md) | OpenClaw 安装、配置向导、高级配置 |
| [docs/FAQ.md](docs/FAQ.md) | 常见问题与排障 |
| [docs/API.md](docs/API.md) | 17 个 MCP 工具 + Python API 参考 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 当前态架构、压缩/遗忘算法、选型对比 |
| [docs/MANUAL_MEMORY.md](docs/MANUAL_MEMORY.md) | 手动记忆管理指南 |
| [docs/ROADMAP.md](docs/ROADMAP.md) | 演进史与路线（含 v5.1.1 移除项说明） |
| [CHANGELOG.md](CHANGELOG.md) | 完整版本历史 |

## License

MIT
