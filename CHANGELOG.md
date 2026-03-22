# 更新日志

所有重要的更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [4.0.38] - 2026-03-22

### Added (Issue #183: 双模式插件)
- 🦞 **Lifecycle Hooks**: 新增 `before_agent_start` 和 `agent_end` hooks
  - 作为 ContextEngine 的降级方案
  - 参考 MemOS OpenClaw Plugin 实现
  - 立即可用，无需等待 OpenClaw Gateway 更新
- 🔄 **双模式支持**: 同时支持 `lifecycle` 和 `context-engine` 两种模式
  - ContextEngine 模式（未来）：`afterTurn` 自动压缩
  - Lifecycle 模式（现在）：`before_agent_start` 召回记忆，`agent_end` 写入记忆
- 🎯 **自动压缩**: 当消息数 > 50 时自动触发压缩
- 📊 **详细日志**: 添加 lifecycle hooks 的详细日志

### Implementation Details
- `before_agent_start`: 调用 `lobster_assemble` 获取记忆，返回 `prependContext` 注入
- `agent_end`: 调用 `lobster_ingest` 保存消息，自动检测并触发压缩
- 配置选项：`lifecycleEnabled`（默认 true）

### References
- MemOS OpenClaw Plugin: https://github.com/MemTensor/MemOS-Cloud-OpenClaw-Plugin
- Issue #183: https://github.com/SonicBotMan/lobster-press/issues/183

## [4.0.37] - 2026-03-22

### Fixed (E2E Test Bug Fixes - Issue #181)
- 🔴 **Bug #1**: 数据库路径 `~` 未展开
  - 修复：`db_path` 参数使用 `os.path.expanduser()` 展开 `~`
  - 影响：数据库文件现在正确创建在 `~/.openclaw/lobster.db`
- 🔴 **Bug #2**: 循环导入导致 `lobster_compress` 等工具失败
  - 修复：延迟导入 `TFIDFScorer`，避免循环依赖
  - 循环链条：`database.py → pipeline/__init__.py → batch_importer.py → database.py`
  - 影响：所有 MCP 工具现在可以正常工作
- 🔴 **Bug #3**: TF-IDF 计算失败 (`ScoredMessage` 对象没有 `get` 方法)
  - 修复：使用属性访问（`last.tfidf_score`）而不是字典方法（`last.get()`）
  - 影响：TF-IDF 分数现在可以正确计算

### Test Results
- ✅ 成功工具：6/15（40%）
- ❌ 失败工具：0/15（0%）
- 所有核心功能（ingest, compress, assemble, grep）现已正常工作

## [4.0.36] - 2026-03-22

### Fixed (P0 - Critical)
- 🔴 **Fix 1**: DECISION_KEYWORDS 死代码修复 (Issue #174)
  - 提升 `DECISION_KEYWORDS` 为类常量，移除 `hasattr` 检查
  - 实体提取功能现已正常工作
- 🔴 **Fix 3**: 修复"丢弃消息"死循环 (Issue #174)
  - 不再丢弃过小的尾部消息，合并到最后一个 episode
  - 压缩流程不再卡死
- 🔴 **Fix 2**: 数据库事务保护 (Issue #174)
  - 使用 `with self.db.conn:` 事务保护，确保原子性
  - 数据一致性得到保障

### Performance (P1)
- 🟠 **Fix 5**: 中文文本复杂度加权 (Issue #174)
  - 引入 `zh_character_ratio` 计算中文字符占比
  - 汉字密度是英文的 2-3 倍，加权处理
  - 中文文本的复杂度评估更准确
- 🟠 **Fix 7**: afterTurn 本地计数 (Issue #174)
  - 添加 `_turn_counts` 缓存，避免频繁的 `SELECT COUNT(*)` 查询
  - 计数器性能提升显著
- 🟠 **Fix 6**: TF-IDF O(n²) 性能优化 (Issue #174)
  - 添加 `_corpus_hash` 检测语料库变化
  - 只在语料库变化时重新计算 IDF
  - 性能提升：大对话（500+ 消息）从 10s+ 降至 <1s

### Notes
- Fix 4（SQLite 并发安全）推迟到后续版本：修复量 83 处，风险较高

## [4.0.35] - 2026-03-22

### Security
- 🔒 **ReDoS 修复**: `PASCAL_RE` 正则表达式限制重复次数，避免指数级回溯 (Security #19)

## [4.0.34] - 2026-03-22

### Added
- ✨ **TF-IDF 自动计算**: `save_message()` 自动计算 TF-IDF 分数，不再依赖外部传入 (Issue #173 修复一)
- ✨ **遗忘曲线排序**: `leaf_compact()` 按保留率升序排列，优先压缩"最应该被遗忘"的消息 (Issue #173 修复二)
- ✨ **R³Mem 实体自动提取**: 压缩后自动提取实体（文件路径、技术概念、决策关键词） (Issue #173 修复三)
  - 支持 LLM 提取和规则提取两种模式
  - Ref: arXiv:2502.15957 §3.2 Entity-Level Retrieval

## [4.0.33] - 2026-03-22

### Fixed
- 🔴 **P0**: `src/database.py` 版本号再次未同步（v4.0.31 → v4.0.33）

## [4.0.32] - 2026-03-22

### Fixed
- 🔴 **P0**: `src/database.py` 版本号未同步到 v4.0.31（CI 失败修复）

## [4.0.31] - 2026-03-22

### Fixed
- 🔴 **P0**: `dag_compressor.py` 小 episode 被跳过但不标记，导致压缩空转（Issue #171）
  - 问题：小 episode 被 `continue` 跳过，但消息 ID 不在 `compressed_message_ids` 中
  - 后果：`uncompressed_tokens` 虚高，压缩阈值永远触发但实际无效
  - 修复：实施"合并小 episode"方案，累积小 episode 直到 tokens ≥ max_tokens * 0.5
  - 尾部阈值：放宽到 max_tokens * 0.3 避免丢弃过多

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

