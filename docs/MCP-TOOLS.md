# MCP 工具参考（v5.1.1，17 个）

> 事实源：`mcp_server/lobster_mcp_server.py` 实际注册。OpenClaw 插件层（index.ts）另有 `lobster_configure`、`lobster_check_context` 两个 TS 工具，不计入此表。

## 读取

| 工具 | 功能 | 必需参数 |
|------|------|----------|
| `lobster_grep` | 全文搜索（FTS5 trigram，<3 字符查询自动 LIKE 回退） | `query` |
| `lobster_describe` | 查看 DAG 摘要结构 | 无（`conversation_id` / `summary_id` 可选） |
| `lobster_expand` | 展开摘要到原始消息 | `summary_id` |
| `lobster_status` | 系统健康报告 | 无 |

## 写入

| 工具 | 功能 | 必需参数 |
|------|------|----------|
| `lobster_ingest` | 消息入库（对话记忆入口） | `conversation_id`, `messages` |
| `lobster_compress` | 触发 DAG 压缩 | `conversation_id` |
| `lobster_correct` | 纠错记忆内容 | `target_type`, `target_id`, `correction_type` |

## 管理

| 工具 | 功能 | 必需参数 |
|------|------|----------|
| `lobster_assemble` | 按三层模型拼装最优上下文（semantic notes > episodic 摘要 > working 原文） | `conversation_id` |
| `lobster_sweep` | 标记衰减消息 | `conversation_id` |
| `lobster_prune` | 删除已衰减消息（默认 dry_run，需 `dry_run=false` 真删） | `conversation_id` |

## 技能 / 多 Agent

| 工具 | 功能 | 必需参数 |
|------|------|----------|
| `lobster_skill` | 查询/安装技能 | `action` + `skill_id`/`conversation_id` |
| `lobster_skill_search` | 搜索技能 | `query`（`scope` 可选，默认 mix） |
| `lobster_skill_publish` | 公开技能 | `skill_id` |
| `lobster_skill_unpublish` | 私有化技能 | `skill_id` |
| `lobster_memory_write_public` | 写入公共记忆 | `content` |

## 工程

| 工具 | 功能 | 必需参数 |
|------|------|----------|
| `lobster_viewer` | Web UI 控制 | 无（`action`/`port` 均有默认值） |
| `lobster_import` | 导入 OpenClaw 历史 | `action` |

## 历史

v2 的 5 个压缩链工具（`compress_session` 等）已在 v5.1.1 移除——它们依赖从未接入主链路的内部流程。演进史见 [ROADMAP.md](ROADMAP.md)。
