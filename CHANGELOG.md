# 更新日志

所有重要的更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [5.0.2] - 2026-04-05

### Fixed (OpenClaw v2026.4.2 Compatibility)
- 🐛 **definePluginEntry()**: 迁移到 `openclaw/plugin-sdk/plugin-entry` 标准导出模式
- 🐛 **kind: "context-engine"**: 在 lobsterEngine.info 中添加类型声明
- 🐛 **debugLog 保护**: `debugLog()` 仅在 `LOBSTER_DEBUG=1` 时写入 `/tmp/lobster-debug.log`（之前 65+ 次无条件写入）
- 🐛 **console.log 删除**: register() 末尾的 bare `console.log` 已移除

### Fixed (Config Consistency)
- 🐛 **maxContextTokens 统一**: schema 默认值和 runtime trailing fallback 均统一为 `40000`
- 🐛 **过时配置删除**: `mcp_server/lobster.config.json` (v1.2.8) 已删除

### Fixed (Security)
- 🔒 **泄漏 API Key**: `tests/integration/test_real_llm.py` 硬编码 ZHIPU API Key → `ZHIPU_API_KEY` 环境变量
- 🔒 **/tmp 路径泄漏**: 4 个测试文件的 `/tmp/lobster-press` → 相对 project-root 路径

### Tests
- ✅ 423 tests passed

## [5.0.1] - 2026-04-05

### Fixed (OpenClaw v2026.4.2 Compatibility)
- 🐛 **peerDependencies 更新**: `>=2026.3.0` → `>=2026.4.2`
- 🐛 **devDependencies 更新**: `openclaw ^2026.3.0` → `^2026.4.2`
- 🐛 **版本号同步**: `package.json` v4.0.97 → v5.0.0，`database.py` v4.0.97 → v5.0.0
- 🐛 **Python 子进程清理**: 添加 `SIGINT`/`SIGTERM` 处理器，防止孤儿进程

### Fixed (P0 Bug Fixes)
- 🔴 **C-HLR+ 公式修正**: `math.exp(-t/h)` → `0.5 ** (t/h)`（12h 后正确得到 50% 保留率，而非 36.8%）
- 🔴 **双重计分移除**: 从 retention score 计算中移除 `access_count` 加成
- 🔴 **Pass 4 无损**: user/assistant 消息正确跳过去重，保持保真度

## [5.0.0] - 2026-04-05

### Added (MemOS 4-Phase Optimization — Core Intelligence)
- ✨ **向量嵌入层**: `src/vector/embedder.py` — OpenAI 兼容 API（默认）+ 离线方案（本地模型）
- ✨ **混合检索器**: `src/vector/retriever.py` — RRF k=60, MMR λ=0.7, 14d 时间衰减
- ✨ **FallbackLLMClient**: `src/llm_client.py` — LLM 提供商降级链（primary → secondary → tertiary）
- ✨ **双衰减参数**: 压缩半衰期 12h + 检索半衰期 14d（两个独立参数）
- ✨ **数据库新增**: `embeddings` 表 — 向量存储层

### Added (MemOS 4-Phase — Skill Evolution)
- ✨ **Skill 数据模型**: `src/skills/models.py` — 技能定义、版本历史、质量评分
- ✨ **Skill 数据库表**: `skills` 表 + `skill_versions` 表 + `skill_evolve_log` 表
- ✨ **任务检测器**: `src/skills/task_detector.py` — 2h 超时判断 + LLM topic 分类
- ✨ **技能进化器**: `src/skills/evolver.py` — 规则过滤 → LLM 评估 → SKILL.md 生成 → 质量评分
- ✨ **MCP Skill 工具**: `lobster_skill get/install/list` — 技能安装管理

### Added (MemOS 4-Phase — Multi-Agent)
- ✨ **MCP 多智能体工具**: `lobster_memory_write_public`, `lobster_skill_search`, `lobster_skill_publish`, `lobster_skill_unpublish`
- ✨ **Owner + Namespace 扩展**: `migrate_v50` 迁移 + owner 过滤器
- ✨ **异步队列 Worker**: `src/async_queue/worker.py` — 后台任务处理

### Added (MemOS 4-Phase — Engineering)
- ✨ **OpenClaw 导入器**: `src/migration/importer.py` — 🦐 前缀支持，openclaw 会话导入
- ✨ **Viewer Web UI**: `src/viewer/server.py` — 127.0.0.1:19876, SHA-256 认证
- ✨ **MCP Phase 4 工具**: `lobster_viewer`, `lobster_import`

### Changed (Architecture)
- 🔄 **22 个 MCP 工具**（原 15 个）: 新增 skill/memory_write_public/skill_search/publish/unpublish/viewer/import
- 🔄 **13 个新 Python 模块**: 向量层、Skill 层、异步队列、Viewer、Migration
- 🔄 **297 个新测试**: 全面覆盖新功能
- 🔄 **maxContextTokens 默认值**: 从 128000 统一为 40000

## [4.0.97] - 2026-03-26

### Added (C-HLR+ 遗忘曲线)
- ✨ **C-HLR+ 算法实现**: 复杂度驱动的自适应遗忘曲线 `h = base_h * (1 + α * complexity)`
- ✨ **数据库字段新增**: `half_life` (半衰期，小时) 和 `review_count` (复习次数)
- ✨ **Pass 4 消息去重**: Jaccard 相似度 > 0.8 的重复消息自动去重
- ✨ **递归 JSON 文本提取**: 支持多层嵌套的 JSON 内容提取

### Changed
- 🔄 **lobster_sweep 集成 C-HLR+**: 使用遗忘曲线算法计算保留率，自动更新 `half_life`
- 🔄 **压缩率提升**: Pass 4 去重后压缩率从 37.4% 提升到 60.9%（+23.5%）
- 🔄 **复杂度计算**: 基于 token 数量、TF-IDF 分数、实体数量、代码检测

### Fixed
- 🐛 **agent_end hook 检查修复**: `data.success` → `data.ingested > 0`
- 🐛 **版本号同步修复**: `src/database.py` Version 字段格式错误

### Technical Details
- 新增文件: `src/pipeline/chlr_scorer.py` (C-HLR+ 评分器)
- 新增文件: `src/pipeline/intent_extractor.py` (意图提取器)
- 修改文件: `src/database.py` (新增 migrate_v41 迁移)
- 修改文件: `src/three_pass_trimmer.py` (新增 Pass 4 去重)

## [4.0.93] - 2026-03-24

### Fixed (安装教程修正)
- 📝 **修正安装教程**: 移除错误的 `npm install -g` 推荐，改为正确的 OpenClaw 插件安装方式
- 📝 **移除不存在的 CLI 命令**: `lobster-press --version` 命令不存在，已从教程中移除
- 📝 **简化安装文档**: 合并"离线安装"到主要安装方式，添加"快速验证命令"
- 🔧 **版本号同步**: 修复 `lobster_mcp_server.py` 中版本号从 v4.0.41 滞后的问题

### Changed
- 安装步骤从 5 步扩展为 6 步，明确区分"安装"和"配置"
- 添加重要提示：LobsterPress 必须安装到 `~/.openclaw/extensions/lobster-press/` 目录

## [4.0.92] - 2026-03-24

### Added (交互式配置向导可靠性增强)
- ✅ **配置保存验证**: 写入配置文件后立即读取验证，确保配置成功保存
- ✅ **API Key 格式测试**: 基本格式检查（OpenAI/Anthropic/智谱/DeepSeek）
- ✅ **配置回滚机制**: 验证失败自动恢复旧配置，不会丢失用户原有配置
- ✅ **错误处理完善**: 友好的错误提示和建议操作

### Fixed
- 🐛 **TypeScript 编译错误**: 修复 `oldConfig` 类型和 `details` 字段问题
- 🐛 **CI 失败**: 所有返回对象添加 `details` 字段，符合 `AgentToolResult` 类型要求

## [4.0.91] - 2026-03-24

### Added (交互式配置向导)
- 🎯 **lobster_configure 工具**: 5 步交互式配置向导
  - 步骤 1: 欢迎和 LLM 选择（使用 LLM 还是 TF-IDF）
  - 步骤 2: LLM Provider 选择（OpenAI/Anthropic/智谱/DeepSeek/自定义）
  - 步骤 3: API Key 输入（带安全提示）
  - 步骤 4: 自动功能确认（C-HLR+/Focus/记忆注入）
  - 步骤 5: 完成并显示配置示例
- 🤖 **AI 主动引导**: AI 可以主动引导用户完成配置
- 📋 **友好提示**: 清晰的配置说明和选项

## [4.0.90] - 2026-03-24

### Changed (C-HLR+ 自动应用)
- ✅ **C-HLR+ 自适应遗忘曲线自动应用**: 每次对话结束后自动调用 `lobster_sweep`
- 🔧 **agent_end hook 增强**: 添加自动调用 `lobster_sweep` 应用遗忘曲线
- 📊 **五大模块更新**: 模块二（C-HLR+）从手动改为自动

### Test Results
- ✅ 用户无需手动调用 `lobster_sweep`
- ✅ 遗忘曲线自动应用于每轮对话
- ✅ 记忆衰减自动标记

## [4.0.89] - 2026-03-24

### Changed (Issue #169: 记忆优先级排序 - 方案C)
- 🧠 **记忆优先级排序**: 按优先级注入记忆（semantic > episodic > working）
  - 长期记忆（semantic/episodic）优先级高于工作记忆（working）
  - 解决了 `.slice(-10)` 截断导致长期记忆被忽略的问题
  - 小文现在能回忆起完整的水果列表（10种），而不是之前的3种
- 📝 **格式优化**: 记忆上下文格式更清晰
  - 使用 `[tier]: content` 格式，易于识别记忆来源
  - 移除 `.slice(-10)` 截断，避免记忆碎片化
  - 字符限制提升到 8000 字符，足够容纳所有记忆
- 🔧 **代码简化**: 移除冗余逻辑
  - 日志从 `assembled.length` 改为 `sortedAssembled.length`
  - 代码更简洁易维护

### Test Results
- ✅ 小文成功回忆起 10 种水果（之前只能回忆 3 种）
- ✅ 记忆注入效率显著提升
- ✅ 长期记忆不再被短期对话挤占

## [4.0.49] - 2026-03-23

### Changed (Issue #52810: MCP 工具模式)
- ⚠️ **Lifecycle Hooks 禁用**: 由于 OpenClaw `api.on()` 不触发，暂时禁用 lifecycle hooks
  - `before_agent_start` 和 `agent_end` hooks 已注释保留
  - 添加 TODO 注释，等待 OpenClaw 修复后恢复
- 📝 **手动记忆管理**: 新增 `docs/MANUAL_MEMORY.md` 指南
  - 说明如何显式调用 `lobster_assemble`（对话开始前）
  - 说明如何显式调用 `lobster_ingest`（对话结束后）
- 📖 **README 更新**: 添加当前状态说明和手动模式指南链接

### Migration Guide
如果你依赖自动记忆管理，需要改为手动调用 MCP 工具：

```python
# 对话开始前
result = lobster_assemble(conversation_id="conv_123", token_budget=128000)

# 对话结束后
result = lobster_ingest(conversation_id="conv_123", messages=[...])
```

详见 [手动记忆管理指南](docs/MANUAL_MEMORY.md)。

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

