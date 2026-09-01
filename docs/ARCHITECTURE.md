# 架构（当前态，v5.1.1）

> 本文描述 v5.1.1 的实际组件拓扑。版本演进（含已移除模块）见 [ROADMAP.md](ROADMAP.md)，逐版变更见 [CHANGELOG.md](../CHANGELOG.md)。

## 组件图

```
┌──────────────────────────────────────────────────────────────┐
│                     OpenClaw 插件层 (index.ts)                │
│  lifecycle hooks: 对话自动存取 · 三策略压缩触发                 │
│  (定时 12h / 紧急 0.85 / 被动—— 阈值为 TS 内置常量)            │
│  TS 工具: lobster_configure · lobster_check_context           │
├──────────────────────────────────────────────────────────────┤
│                     MCP Server (17 工具)                      │
│   读取: grep / describe / expand / status                     │
│   写入: ingest / compress / correct                           │
│   管理: assemble / sweep / prune                              │
│   技能: skill×4 · memory_write_public                         │
│   工程: viewer · import                                       │
├──────────────────────────────────────────────────────────────┤
│                        核心引擎 (src/)                        │
│  database.py        SQLite 单文件存储（无损层，消息永不删除）    │
│  dag_compressor     DAG 分层压缩 + context_items 视图管理      │
│  incremental_compressor  使用率驱动自动压缩 (0.60/0.75 分界)   │
│  chlr_scorer        C-HLR+ 遗忘曲线 R(t)=0.5^(t/h) 双半衰期    │
│  semantic_memory    语义笔记（知识提取/维护）                   │
│  conflict_detector  矛盾检测（NLI + 规则回退，主张动词门槛）    │
│  skills/            技能进化：任务检测→SKILL.md 生成→评分      │
│  viewer/            本地 Web UI (127.0.0.1, SHA-256 认证)     │
├──────────────────────────────────────────────────────────────┤
│                FTS5 trigram 中文全文索引                       │
│        ≥3 字符走索引 · 短查询 LIKE 回退 · 查询全转义           │
└──────────────────────────────────────────────────────────────┘
```

## 三层记忆模型

`lobster_assemble` 按以下优先级拼装上下文：

1. **semantic** — SemanticMemory 笔记（稳定知识：决策/偏好/事实，经矛盾检测维护）
2. **episodic** — DAG 压缩摘要（对话事件的分层概括，可 `lobster_expand` 回溯原文）
3. **working** — 原始消息（近期未压缩内容）

## 压缩如何做到"无损"

- 压缩 = 在 context_items 视图中以摘要**替换**原消息的展示位；`messages` 表本体永不删除
- light 策略（使用率 60–75%）只做语义去重；aggressive（≥75%）走 DAG 分层压缩
- 任何摘要节点都保留子消息 ID 链，`lobster_expand` 沿链回溯到原文
- `lobster_prune` 是唯一物理删除入口，且默认 `dry_run=true`

## 选型对比（核实日期 2026-09-01）

| | LobsterPress | mem0 | letta | MemOS |
|---|---|---|---|---|
| 形态 | 本地嵌入式引擎 | 托管向量记忆服务 | 有状态 Agent 运行时 | 记忆操作系统框架 |
| 存储 | SQLite 单文件 | 云向量库 | 自管理 | 框架定义 |
| 中文检索 | ✅ trigram 原生 | embedding 依赖 | embedding 依赖 | 视实现 |
| 部署依赖 | 无（OpenClaw 插件即装） | API Key + 网络 | 常驻服务 | 框架栈 |
| 技能进化 | ✅ 对话→SKILL.md | ✗ | ✗ | ✗ |
| 矛盾检测 | ✅ NLI+规则 | ✗ | ✗ | ✗ |

**什么时候别选我**：需要多机共享记忆托管、需要语义向量检索多模态内容、或需要完整 Agent 运行时（而不只是记忆层）时，mem0 / letta 更合适。

## 项目结构

```
src/
├── database.py               # SQLite 存储层（无损）
├── dag_compressor.py         # DAG 压缩引擎
├── incremental_compressor.py # 使用率驱动自动压缩
├── semantic_memory.py        # 语义笔记
├── llm_client.py             # LLM fallback 链
├── llm_providers.py          # 8 个提供商适配
├── agent_tools.py            # 函数式 Python API
├── skills/                   # 技能进化
├── viewer/                   # Web UI
├── migration/                # OpenClaw 导入
└── pipeline/                 # 评分/去重/分割等管线
mcp_server/                   # MCP 17 工具
index.ts                      # OpenClaw 插件入口
```

> v5.0 曾包含 `src/vector/`（向量检索）与 `src/async_queue/`（后台队列），实测为未接线死代码后于 v5.1.1 移除——详见 [ROADMAP.md](ROADMAP.md)。
