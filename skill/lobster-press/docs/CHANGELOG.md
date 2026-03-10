# 更新日志

所有重要的更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.2.1] - 2026-03-10

### ✨ 新增

#### 质量守卫（Quality Guard）(#30)
- **decision_preserved** - 关键决策保留检查
- **config_intact** - 配置信息完整检查
- **context_coherent** - 上下文连贯性检查
- **自动回滚** - 质量不达标时自动恢复原始会话

#### 架构说明（#36）
- README 添加新旧系统关系表
- BENCHMARK 添加测试方法论
- v1.3.0 架构计划文档

### 🔧 优化
- `compression_validator.py` 升级到 v1.2.1（质量守卫）

### 📋 关闭 Issues
- #25 Token 成本透明度 ✅
- #26 动态模型选择 ✅
- #30 压缩质量守卫 ✅
- #36 Shell/Python 双栈架构 ✅

---

## [1.2.0] - 2026-03-10

### ✨ 新增

#### Zero-cost 本地压缩 (#35)
- **API 调用**：0（local 模式）
- **压缩成本**：$0.00
- **基于 RFC #34 实现**

#### TF-IDF 三层叠加评分
- Layer 1: TF-IDF（词汇稀有度）
- Layer 2: 结构性信号（规则）
- Layer 3: 时间衰减

#### 语义去重
- 余弦相似度 > 0.82 视为重复
- 保留重要性更高的消息

#### 提取式摘要
- 零 API 成本
- 不生成新 token
- 不引入 AI 幻觉

#### 分层模式
- local: 纯本地，$0
- hybrid: 可选增强
- api: API 模式

### 📊 性能提升

| 上下文 | 旧版净收益 | 新版净收益 |
|--------|----------|----------|
| 5k | -350 | +500 |
| 15k | +2,150 | +3,500 |
| 30k | +5,900 | +8,000 |

### 🔧 新文件
- `scripts/tfidf_scorer.py`
- `scripts/semantic_dedup.py`
- `scripts/extractive_summarizer.py`
- `scripts/lobster_press_v120.py`
- `requirements.txt`

### 🙏 贡献者
- 小华 (Xiao Hua) - Code Review

---

## [1.1.1] - 2026-03-10

### ✨ 新增

#### Token 精确计量 (#33)
- 使用 tiktoken 进行精确 Token 计数
- 支持中文场景（误差从 30% 降至 5%）

#### 净收益校验
- 压缩前检查是否值得
- 避免负收益压缩
- 设置最小 Token 阈值（4000）

#### 上下文连贯性
- 强制保留最近 N 条消息
- 防止 AI "失忆"

#### 动态模型选择
- 根据策略自动选择最优模型
- light → glm-4-flash
- medium → glm-4
- heavy → claude-3-opus

### 🔧 新文件
- `scripts/token_counter.py`
- `scripts/compression_validator.py`
- `scripts/lobster_press_v111.py`
- `docs/BENCHMARK.md`
- `requirements.txt`

### 📋 关联 Issues
- #25 Token 成本透明度
- #26 动态模型选择
- #30 上下文连贯性
- #32 五项核心优化

### 🙏 贡献者
- 小华 (Xiao Hua) - Code Review

---

## [1.1.0] - 2026-03-09

### ✨ 新增

#### OpenClaw 集成协调器 (#21)
- **功能**：与 OpenClaw 内置 Compaction 功能协调工作，避免重复压缩
- **新增文件**：
  - `scripts/lobster-openclaw-coordinator.sh` - 协调器脚本
  - `docs/OPENCLAW-INTEGRATION.md` - 集成文档
  - `examples/openclaw-integration-config.json` - 配置示例
- **分层策略**：
  | Token 使用率 | 处理方式 |
  |-------------|----------|
  | < 60% | 无需处理 |
  | 60-80% | 龙虾饼报告 |
  | 80-90% | 龙虾饼轻度压缩（可选） |
  | 90-95% | 等待 OpenClaw 或龙虾饼压缩 |
  | > 95% | OpenClaw 自动压缩 |
- **协调功能**：
  - 检测 OpenClaw compaction 历史
  - 跳过近期已压缩的会话（默认 1 小时窗口）
  - JSON 输出支持（供程序调用）

### 📝 文档

#### 更新文档
- README.md 添加 OpenClaw 集成文档链接
- 新增 `examples/openclaw-integration-config.json` 配置示例

### 🙏 贡献者

- 小华 (Xiao Hua) - OpenClaw 集成协调器

---

## [1.0.1] - 2026-03-08

### 🐛 修复

#### 本地压缩兼容性问题 (#1)
- **问题**：本地压缩模式使用 `grep -oE '[\u4e00-\u9fa5]'` 导致语法错误
- **影响**：API 限流时无法回退到本地压缩
- **修复**：
  - 添加跨平台兼容性检测（GNU grep vs BSD grep）
  - GNU grep 使用 `-P` (Perl 正则)
  - BSD/macOS grep 使用传统正则 `[一-龥]`
  - 添加最终 fallback 方案

#### Systemd 服务配置错误 (#2)
- **问题**：`User=%u` 导致服务启动失败（错误码 216/GROUP）
- **影响**：定时任务无法运行
- **修复**：
  - 移除 `User=%u` 配置
  - 使用 `%h` 变量替代硬编码路径
  - 添加 `WorkingDirectory` 配置

#### AUTO_APPLY 环境变量缺失 (#3)
- **问题**：定时任务中未设置 `AUTO_APPLY`，导致压缩结果不会自动应用
- **影响**：需要手动确认才能应用压缩
- **修复**：
  - 添加默认值 `AUTO_APPLY=${AUTO_APPLY:-true}`
  - Systemd 服务中添加 `Environment=AUTO_APPLY=true`

#### 历史文件未自动创建 (#4)
- **问题**：`compression-history.md` 文件不存在导致记录失败
- **影响**：无法查看压缩历史和学习效果
- **修复**：
  - 脚本启动时自动创建历史文件
  - 路径改为 `~/.lobster-press/compression-history.md`

### ✨ 新增

#### API 限流处理 (#5)
- **功能**：自动重试机制
- **特性**：
  - 最多重试 3 次
  - 指数退避（2s → 4s → 8s）
  - 自动检测限流错误（错误码 1302）
  - 详细的错误日志

#### 日志级别配置
- **功能**：支持通过环境变量控制日志详细程度
- **用法**：`Environment=LOG_LEVEL=INFO`
- **级别**：DEBUG, INFO, WARN, ERROR

#### 更好的错误处理
- API Key 读取 fallback 机制
- 配置文件不存在的容错处理
- 详细的错误提示信息

### 🔧 优化

#### 路径配置改进
- 脚本路径：`$HOME/bin/` → `%h/bin/`
- 历史文件：`~/.openclaw/workspace/memory/` → `~/.lobster-press/`
- Engine 路径：`$HOME/message-importance-engine.sh` → `$HOME/bin/`

#### 代码质量
- 添加详细的注释
- 改进错误提示信息
- 统一代码风格

### 📝 文档

#### 新增文档
- `CHANGELOG.md` - 版本更新记录
- `docs/CONFIGURATION.md` - 详细配置指南（已有）

#### 更新文档
- README.md 添加 v1.0.1 版本说明
- 修复 systemd 配置示例
- 添加常见问题解答

## [1.0.0] - 2026-03-08

### ✨ 首次发布

#### 核心功能
- 🦞 智能上下文压缩引擎 v5
- 🧠 消息重要性评估引擎
- 📊 自适应学习系统
- 🔮 预测性压缩
- 💰 成本优化器

#### 压缩策略
- Light（轻度）：节省 10-15%，保留 95% 信息
- Medium（中度）：节省 20-30%，保留 85% 信息
- Heavy（深度）：节省 40-50%，保留 70% 信息

#### Systemd 集成
- lobster-compress.timer - 每 30 分钟预测性压缩
- lobster-learning.timer - 每小时智能学习
- lobster-optimizer.timer - 每天成本优化

#### API 支持
- GLM 系列（智谱 AI）
- OpenAI 系列
- Claude 系列
- 本地压缩（离线 fallback）

---

## 版本说明

- **主版本号（Major）**：不兼容的 API 修改
- **次版本号（Minor）**：向下兼容的功能性新增
- **修订号（Patch）**：向下兼容的问题修正

## 链接

- [GitHub Releases](https://github.com/SonicBotMan/lobster-press/releases)
- [问题跟踪](https://github.com/SonicBotMan/lobster-press/issues)
- [更新日志](https://github.com/SonicBotMan/lobster-press/blob/master/CHANGELOG.md)
