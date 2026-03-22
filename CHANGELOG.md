# 更新日志

所有重要的更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [4.0.30] - 2026-03-22

### Fixed
- 🔴 **P0**: `afterTurn` 策略一/二缺少异常捕获，异常冒泡可能中断对话（Issue #169）
  - 问题：策略一（定时）和策略二（紧急）没有 try/catch，异常会冒泡到 Gateway
  - 修复：为两种策略添加 try/catch，记录错误日志但不中断对话
  - 更新：异常处理注释，明确三种策略均捕获异常

## [4.0.29] - 2026-03-22

### Fixed
- 🟠 **P1**: `assemble()` 方法 catch 块缺少错误日志，失败时完全静默（Issue #170）
  - 问题：assemble 失败时没有任何日志记录，开发者和运维无法感知
  - 修复：添加 `api.logger.error()` 调用，与 `prepareContext`、`_getTurnCount` 等方法保持一致

## [4.0.28] - 2026-03-22

### Fixed
- 🔴 **P0**: `ingest()` 忽略 `sessionKey` 参数，导致特定场景下消息丢失（Issue #172）
  - 问题：`ingest` 只用 `sessionId`，而 `prepareContext` 会 fallback 到 `sessionKey`，导致 key 不一致
  - 修复：与 `prepareContext` 保持一致的 fallback 逻辑：优先 `sessionId`，fallback 到 `sessionKey`
  - 新增：无有效 conversationId 时返回 `{ ingested: false, error: "no conversationId" }` 并记录警告日志

## [4.0.27] - 2026-03-22

### Added
- 🟠 **P1**: `ingest()` 失败时添加警告日志，便于监控消息丢失（Issue #166 P0-2）
  - 新增：`api.logger.warn()` 记录 ingest 失败详情

### Changed
- 🟡 **P2**: `maxContextTokens` 默认值从 128000 调整为 40000（Issue #166 P1-1）
  - 在 `configSchema` 中设置默认值，而非使用方 fallback
  - 40000 tokens ≈ 120000 字符，适合大多数上下文窗口

## [4.0.26] - 2026-03-22

### Fixed
- 🔴 **P0**: `cwd` 路径错误 - `join(__dirname, "..")` 指向错误目录，Python 无法找到 `mcp_server` 模块（Issue #167 Bug #4）
  - 修复：改为 `__dirname`（index.ts 在包根目录）
- 🟠 **P1**: `bootPromise` 竞态条件 - finally 无条件清除导致可能启动多个 Python 子进程（Issue #167 Bug #1）
  - 修复：只有当前进程成功启动才清除
- 🟠 **P1**: `afterTurn` 中 `tokenBudget` 来源不一致 - 未读取 `pluginConfig.maxContextTokens`（Issue #167 Bug #2）
  - 修复：优先读取 `pluginConfig.maxContextTokens`
- 🟡 **P2**: `prepareContext` 截断逻辑错误 - `* 3` 计算导致 384000 字符上限，逻辑混淆（Issue #167 Bug #3）
  - 修复：改为固定 4000 字符上限（摘要注入，非全量上下文）
- 🟡 **P2**: `crypto.randomUUID()` 兼容性 - 部分旧版 Node.js 不支持（Issue #167 Bug #5）
  - 修复：改用 `Date.now() + Math.random()` 生成 ID

## [4.0.25] - 2026-03-21

### Fixed
- 🟠 **P1**: `assemble()` token_budget 默认值从 8000 改为 128000，与 `afterTurn` 保持一致（Issue #163 P1-4）
  - 之前：assemble 使用 8000，afterTurn 使用 128000，相差 16 倍
  - 现在：统一使用 128000

### Housekeeping
- 📋 **P2**: 版本号同步（Issue #163 P2）
  - src/agent_tools.py: v4.0.16 → v4.0.25
  - mcp_server/lobster_mcp_server.py: v4.0.16 → v4.0.25

### Notes
- P0-1（turn_count 测试覆盖）是误报：`tests/unit/test_v400.py:175` 已有 `test_get_turn_count` 测试
- P0-2（ingest 静默降级）是设计决策，调用方可根据 `ingested: false` 决定是否重试

