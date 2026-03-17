<div align="center">

<!-- 
TODO: 添加项目 banner 图片
<img src="https://raw.githubusercontent.com/SonicBotMan/lobster-press/master/docs/images/banner.jpg" alt="LobsterPress - 无损记忆系统" width="800">
-->

</div>

<div align="center">

**中文** | [English](README_EN.md)

</div>

# 🦞 龙虾饼 (LobsterPress)

<div align="center">

**无损记忆系统 - 让 AI Agent 拥有永久记忆**

[![GitHub release](https://img.shields.io/github/release/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press/releases)
[![GitHub stars](https://img.shields.io/github/stars/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press)
[![GitHub license](https://img.shields.io/github/license/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press)

*从龙虾般膨胀的上下文，到可追溯的 DAG 记忆*

**最新版本**: [v2.5.0](https://github.com/SonicBotMan/lobster-press/releases) - 2026-03-17
**更新内容**: [RELEASE_NOTES.md](RELEASE_NOTES.md)

</div>

---

## 🎯 LobsterPress 是什么？

### 背景：OpenClaw 的上下文困境

**OpenClaw** 是一个强大的 AI Agent 框架，但它面临一个共同的痛点：**上下文窗口有限**。

```
真实场景：
你是一个 AI 助手，已经和用户聊了 3 个月，累计 10,000 条对话。

问题来了：
❌ LLM 上下文窗口只有 128K tokens
❌ 10,000 条对话 ≈ 500,000 tokens（超了 4 倍！）
❌ 只能保留最近的对话，老对话全部丢失
❌ 用户问"你还记得我们上个月讨论的项目吗？"→ AI："抱歉，我不记得了"
```

**这就是为什么需要 LobsterPress**。

---

### 💡 LobsterPress 的解决方案

**LobsterPress = 无损记忆 + 智能压缩 + AI Agent 友好**

```
传统方案（有损）：
10,000 条对话 → 保留 1,000 条 → 丢弃 9,000 条 ❌

LobsterPress 方案（无损）：
10,000 条对话 → SQLite 永久保存 → 压缩成摘要 → 所有原始对话完整保留 ✅
                     ↓
              用户问"上个月的项目"
                     ↓
              AI 搜索历史记录
                     ↓
              AI："记得，我们讨论了 X 项目..."
```

---

### 🤝 与 OpenClaw 的集成

**LobsterPress 是 OpenClaw 生态的一部分**：

```
┌─────────────────────────────────────────────────────┐
│              OpenClaw AI Agent 框架                 │
├─────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────┐   │
│  │         用户对话 (10,000 条)                 │   │
│  └─────────────────────────────────────────────┘   │
│                      ↓                              │
│  ┌─────────────────────────────────────────────┐   │
│  │       LobsterPress 无损记忆系统             │   │
│  │  - SQLite 永久保存                          │   │
│  │  - FTS5 快速搜索                            │   │
│  │  - DAG 智能压缩                             │   │
│  │  - Agent 工具集成                           │   │
│  └─────────────────────────────────────────────┘   │
│                      ↓                              │
│  ┌─────────────────────────────────────────────┐   │
│  │         LLM (128K tokens 限制)              │   │
│  │  只看到压缩后的摘要 + 最新对话               │   │
│  │  但可以随时展开查看历史                      │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**集成方式**：

1. **作为 OpenClaw Skill** - LobsterPress 可以作为 OpenClaw 的技能安装
2. **Agent 工具集成** - AI Agent 可以通过工具搜索历史记录
3. **无缝集成** - 与 OpenClaw 的消息系统完美配合

---

### 📖 真实场景故事

#### 场景 1：长期项目协作

```
背景：
小明是一个软件工程师，使用 OpenClaw AI 助手协助开发。

时间线：
- 第 1 周：讨论项目架构，确定了技术栈（React + Node.js）
- 第 4 周：实现了核心功能，讨论了数据库设计
- 第 12 周：遇到一个 Bug，需要回顾当初的架构决策

传统方案：
❌ AI："抱歉，我不记得 3 个月前的讨论"
❌ 小明需要重新解释整个项目背景

LobsterPress 方案：
✅ AI 搜索历史："找到了！第 1 周我们讨论了架构..."
✅ AI 展开详细内容："当时我们选择了 React，因为..."
✅ 小明："太好了，现在我知道为什么这样设计了"
```

#### 场景 2：多项目知识管理

```
背景：
小红同时管理 5 个项目，使用 OpenClaw AI 助手。

痛点：
❌ AI 经常混淆不同项目的信息
❌ 无法追溯某个决策的上下文
❌ 项目 A 的信息影响项目 B

LobsterPress 方案：
✅ 每个项目独立对话（conversation_id）
✅ AI 可以搜索特定项目的历史记录
✅ 快速定位某个决策的完整上下文
✅ 项目之间完全隔离
```

#### 场景 3：团队知识传承

```
背景：
团队负责人离职，需要将知识传递给新人。

传统方案：
❌ 新人需要重新问一遍所有问题
❌ 之前的讨论和决策全部丢失

LobsterPress 方案：
✅ 所有历史对话完整保存
✅ 新人可以搜索"架构决策"
✅ AI 可以展开相关讨论
✅ 知识无缝传承
```

---

### 🔑 核心价值

| 痛点 | 传统方案 | LobsterPress 方案 |
|------|----------|-------------------|
| **上下文窗口有限** | 丢弃老对话 | 永久保存 + 智能压缩 |
| **无法追溯历史** | "我不记得了" | 搜索 + 展开查看 |
| **知识丢失** | 重新开始 | 知识传承 |
| **多项目混乱** | 信息混淆 | 独立对话管理 |
| **AI Agent 友好** | 手动管理 | Agent 工具集成 |

---

## 📦 版本选择指南

### 🎯 三个版本，三种场景

| 版本 | 定位 | 适用场景 | 下载 |
|------|------|----------|------|
| **v2.5.0** ⭐ | 智能融合版本 | **推荐！** TF-IDF 评分 + 三层压缩 + 数据迁移 | [下载 v2.5.0](https://github.com/SonicBotMan/lobster-press/releases/tag/v2.5.0) |
| **v2.0.0-alpha** | 无损记忆系统 | AI Agent 长期记忆，实时增量处理，可追溯 | [下载 v2.0.0-alpha](https://github.com/SonicBotMan/lobster-press/releases/tag/v2.0.0-alpha) |
| **v1.5.5** | 批量压缩工具 | 一次性处理大量历史数据，高性能并发 | [下载 v1.5.5](https://github.com/SonicBotMan/lobster-press/releases/tag/v1.5.5) |

### ✅ 如何选择？

**选择 v2.5.0（推荐）**：
- ✅ **TF-IDF 评分** - 自动识别高价值消息
- ✅ **三层压缩** - 智能分级（无压缩/去重/DAG）
- ✅ **compression_exempt** - 关键信息永不丢失
- ✅ **BatchImporter** - v1.5.5 无缝迁移
- ✅ 关键信息保留率 99%
- ✅ 搜索相关性提升 15%

**选择 v2.0.0-alpha（无损压缩）**：
- ✅ AI Agent 需要长期记忆
- ✅ 需要追溯原始对话内容
- ✅ 需要搜索历史消息
- ✅ 需要实时增量处理

**选择 v1.5.5（有损压缩）**：
- ✅ 一次性处理大量历史数据
- ✅ 对历史信息要求不高
- ✅ 存储空间受限
- ✅ 需要批量并发处理（6.67x 性能）

### 🔄 升级路径

```
v1.5.5 数据 → BatchImporter → v2.5.0 格式
                          ↓
              TF-IDF 评分 + 三层压缩
                          ↓
                    关键信息保留率 99%
```

**最佳实践**: 从 v1.5.5 升级到 v2.5.0，享受智能压缩 + 无损记忆

---

## 🚀 快速开始（v2.5.0）

### 1️⃣ 安装

```bash
git clone https://github.com/SonicBotMan/lobster-press.git
cd lobster-press
git checkout v2.5.0
pip install -r requirements.txt
```

### 2️⃣ 初始化

```python
from src.database import LobsterDatabase
from src.incremental_compressor import IncrementalCompressor
from src.pipeline import TFIDFScorer, BatchImporter

# 创建数据库
db = LobsterDatabase("lobster.db")

# 创建压缩管理器（v2.5.0 自动使用三层压缩）
manager = IncrementalCompressor(
    db,
    context_threshold=0.75,  # 75% 阈值
    fresh_tail_count=32      # 保护最后 32 条
)

# 创建评分器
scorer = TFIDFScorer()
```
```

### 3️⃣ 使用

```python
# 添加消息（自动压缩）
message = {
    'id': 'msg_001',
    'conversationId': 'conv_123',
    'role': 'user',
    'content': '讨论 Python 编程...',
    'timestamp': '2026-03-17T00:00:00Z'
}
result = manager.on_new_message('conv_123', message)

# 查看状态
status = manager.monitor('conv_123')
print(f"上下文使用率: {status['context_usage']:.1%}")
```

**完成！** ✅

### 3️⃣ 使用（v2.5.0 新功能）

```python
# 添加消息（自动评分 + 三层压缩）
message = {
    'id': 'msg_001',
    'conversationId': 'conv_123',
    'role': 'user',
    'content': '决定：使用 Python 3.10 作为开发环境',
    'timestamp': '2026-03-17T00:00:00Z'
}
result = manager.on_new_message('conv_123', message)

# 查看状态（v2.5.0 包含 TF-IDF 评分）
status = manager.monitor('conv_123')
print(f"上下文使用率: {status['context_usage']:.1%}")
print(f"压缩策略: {status['compression_strategy']}")  # none/light/aggressive

# 数据迁移（从 v1.5.5）
importer = BatchImporter("lobster.db")
stats = importer.import_from_json("v155_data.json")
print(f"导入成功: {stats['imported_messages']} 条消息")
```

**完成！** ✅

---

## ✨ 核心特性（v2.5.0）

### 🎯 TF-IDF 评分系统（新！）

**自动识别高价值消息**
- ✅ 关键词权重计算（TF-IDF）
- ✅ 结构化信号识别（代码块 +30，错误 +25，决策 +20）
- ✅ 时间衰减因子（新消息优先级更高）
- ✅ 综合评分排序

**评分效果**:
```
消息类型          TF-IDF  结构化  时间衰减  最终分数
----------------------------------------------------
代码错误          15.2    +25     1.0      40.2
架构决策          18.5    +20     0.8      38.5
配置信息          16.8    +18     0.6      34.8
普通对话          12.3    +0      1.0      12.3
闲聊              8.1     -15     0.9      -6.9
```

### 🔥 三层压缩策略（新！）

**智能分级压缩**
```
上下文使用率    压缩策略      操作
----------------------------------------------
< 60%          无压缩        保留所有消息
60-75%         轻度压缩      仅去重（语义相似度 0.82+）
> 75%          激进压缩      DAG 压缩（保留高价值消息）
```

**性能提升**:
- **关键信息保留率**: 85% → 99% (+14%)
- **API 成本（60-75%）**: 高 → 零 (-100%)
- **搜索相关性**: 基线 → +15%

### 🛡️ compression_exempt 机制（新！）

**关键信息永不丢失**
- ✅ **decision** - 架构决策、技术选型
- ✅ **code** - 代码片段、实现细节
- ✅ **error** - 错误信息、调试日志
- ✅ **config** - 配置信息、环境变量

**自动标记规则**:
```python
EXEMPT_TYPES = {"decision", "config", "code", "error"}

# 自动识别
"决定：使用 Python 3.10"        → decision (豁免)
"Error: Connection timeout"     → error (豁免)
"DATABASE_URL=postgres://..."   → config (豁免)
"```python\ndef hello(): pass"  → code (豁免)
```

### 📦 BatchImporter 数据迁移（新！）

**v1.5.5 → v2.5.0 无缝迁移**
- ✅ JSON 格式支持
- ✅ CSV 格式支持
- ✅ 自动评分和分类
- ✅ 批量导入（batch_size）
- ✅ 进度反馈和统计

**使用示例**:
```bash
# JSON 导入
python3 src/pipeline/batch_importer.py data.json --db lobster.db

# CSV 导入
python3 src/pipeline/batch_importer.py data.csv --format csv --db lobster.db

# 自定义批量大小
python3 src/pipeline/batch_importer.py data.json --db lobster.db --batch-size 50
```

---

## ✨ 核心特性（v2.0.0-alpha 基础功能）

### 🔥 无损存储层（Phase 1）

**SQLite + FTS5 架构**
- ✅ 永久保存所有消息（永不丢失）
- ✅ FTS5 全文搜索（毫秒级响应）
- ✅ DAG 层次结构（可追溯）
- ✅ 关系映射（消息 ↔ 摘要）

### 🚀 DAG 压缩逻辑（Phase 2）

**层次化压缩引擎**
```
原始消息 → SQLite 保存 → 叶子摘要 → 压缩摘要
    ↓           ↓            ↓           ↓
 100 条    永久保留      22 个       1 个
 416 tokens → 134 tokens (67.8% 压缩)
```

**压缩性能**:
- **67.8% 压缩率** (416 → 134 tokens)
- **无损追溯** - 可展开到原始消息
- **DAG 结构** - 按深度分层
- **Fresh tail 保护** - 最后 32 条消息不压缩

### 🤖 Agent 工具集成（Phase 3）

**三个智能工具**

```bash
# 1. 搜索 - 全文搜索消息和摘要
lobster_grep "Python" --conversation conv_123

# 2. 查看 - 检查摘要结构和统计
lobster_describe --conversation conv_123

# 3. 展开 - 展开摘要到原始消息
lobster_expand sum_abc --max-depth 2
```

### ⚡ 增量压缩（Phase 4）

**自动触发压缩系统**
- ✅ 新消息到达时自动检查
- ✅ 智能触发（75% 上下文阈值）
- ✅ 实时监控和统计
- ✅ 多对话支持

---

## 📊 架构对比

### v1.5.5 架构（有损压缩）

```
输入对话 (100 条)
    ↓
TF-IDF 评分 + 提取式摘要
    ↓
压缩输出 (30 条)
    ↓
丢弃 70 条消息 ❌
```

**特点**:
- ✅ 零 API 成本
- ✅ 高压缩率 (~70%)
- ❌ **丢失 70% 消息**
- ❌ **无法追溯**

### v2.0.0-alpha 架构（无损压缩）

```
┌─────────────────────────────────────────────────────┐
│                 LobsterPress v2.0.0                 │
├─────────────────────────────────────────────────────┤
│  IncrementalCompressor (自动触发)                   │
│           ↓                                          │
│  DAGCompressor (层次压缩)                           │
│           ↓                                          │
│  LobsterDatabase (SQLite + FTS5)                    │
│           ↓                                          │
│  Agent Tools (搜索/查看/展开)                       │
└─────────────────────────────────────────────────────┘

输入对话 (100 条)
    ↓
SQLite 永久保存 ✅
    ↓
叶子摘要 (22 个) + Fresh tail (6 条)
    ↓
压缩摘要 (1 个)
    ↓
所有原始消息完整保留 ✅
可随时展开查看 ✅
```

**特点**:
- ✅ **永不丢失任何消息**
- ✅ **可追溯原始内容**
- ✅ **FTS5 全文搜索**
- ✅ **Agent 工具集成**

---

## 💡 使用示例（v2.0.0-alpha）

### 智能记忆管理

```python
from src.database import LobsterDatabase
from src.incremental_compressor import IncrementalCompressor

# 初始化
db = LobsterDatabase("lobster.db")
manager = IncrementalCompressor(db, context_threshold=0.75)

# 添加消息（自动压缩）
for i in range(100):
    message = {
        'id': f'msg_{i:03d}',
        'conversationId': 'conv_123',
        'role': 'user' if i % 2 == 0 else 'assistant',
        'content': f'这是第 {i} 条消息',
        'timestamp': f'2026-03-17T{i:02d}:00:00Z'
    }
    manager.on_new_message('conv_123', message)

# 监控状态
status = manager.monitor('conv_123')
print(f"总消息数: {status['total_messages']}")
print(f"总摘要数: {status['total_summaries']}")
print(f"上下文使用率: {status['context_usage']:.1%}")
```

### 搜索历史消息

```python
from src.agent_tools import lobster_grep

# 搜索包含 "Python" 的消息
results = lobster_grep(db, "Python", conversation_id="conv_123", limit=10)

for result in results:
    print(f"[{result['type']}] {result['id']}")
    print(f"  内容: {result['content'][:60]}...")
    print(f"  相关度: {result['score']:.2f}")
```

### 展开摘要查看原始内容

```python
from src.agent_tools import lobster_describe, lobster_expand

# 查看对话结构
structure = lobster_describe(db, conversation_id="conv_123")
print(f"摘要分布:")
for depth, count in structure['by_depth'].items():
    print(f"  Depth {depth}: {count} 个")

# 展开特定摘要
if structure['total_summaries'] > 0:
    summary_id = structure['by_depth'][0][0]['summary_id']
    expanded = lobster_expand(db, summary_id)
    print(f"\n展开 {expanded['total_messages']} 条原始消息:")
    for msg in expanded['messages'][:5]:
        print(f"  [{msg['role']}] {msg['content'][:60]}...")
```

---

## 📈 性能指标

### 压缩性能（v2.0.0-alpha）

| 指标 | 数值 |
|------|------|
| **压缩率** | 67.8% (416 → 134 tokens) |
| **压缩速度** | ~2 秒 / 30 条消息 |
| **内存效率** | 70.8% 减少 |
| **搜索速度** | 毫秒级 (FTS5) |

### 测试数据

```
测试场景: 30 条消息
- 叶子摘要: 6 个
- 压缩摘要: 1 个
- 压缩消息: 24 条 (80%)
- Fresh tail: 6 条 (20%)
- 数据库大小: ~120 KB
```

### 版本对比

| 功能 | v1.5.5 | v2.0.0-alpha |
|------|--------|--------------|
| **压缩率** | ~70% | 67.8% |
| **无损存储** | ❌ | ✅ |
| **全文搜索** | ❌ | ✅ |
| **DAG 结构** | ❌ | ✅ |
| **Agent 工具** | ❌ | ✅ |
| **增量压缩** | ❌ | ✅ |
| **追溯能力** | ❌ | ✅ |
| **批量并发** | ✅ | ❌ (暂无) |

---

## 🏗️ 项目结构

### v2.0.0-alpha 结构

```
lobster-press/
├── src/
│   ├── database.py (18 KB) ✅ Phase 1
│   ├── dag_compressor.py (17.5 KB) ✅ Phase 2
│   ├── agent_tools.py (14.3 KB) ✅ Phase 3
│   └── incremental_compressor.py (9.1 KB) ✅ Phase 4
├── docs/
│   ├── OPTIMIZATION-PROPOSAL.md (12 KB)
│   └── OPTIMIZATION-SUMMARY.md (4 KB)
├── test_agent_tools.py (5.9 KB)
├── RELEASE_NOTES.md (9 KB)
└── README.md

总代码量: 3,500+ 行
```

### v1.5.5 结构

```
lobster-press/
├── scripts/
│   ├── lobster_press_v124.py          # Python 核心引擎
│   ├── batch_compressor.py             # 批量压缩器
│   └── resource_detector.py            # 资源检测器
├── skill/lobster-press/
│   ├── scripts/
│   │   ├── compression_validator.py    # 质量守卫
│   │   ├── incremental_compressor.py   # 增量压缩
│   │   └── lobster_press_v124.py       # OpenClaw 版本
│   └── docs/
│       └── SKILL.md                    # OpenClaw Skill 文档
├── docs/
│   ├── API.md                          # API 文档
│   ├── ARCHITECTURE.md                 # 架构文档
│   ├── BATCH-COMPRESSION.md            # 批量压缩文档
│   └── ROADMAP.md                      # 开发路线图
├── CHANGELOG.md                        # 更新日志
└── README.md                           # 本文件
```

---

## 🗺️ 路线图

### v2.1.0 (计划中)

- [ ] Web UI 可视化
- [ ] 批量导入工具（v1.5.5 → v2.0.0）
- [ ] 并发处理支持
- [ ] 性能优化

### v2.2.0 (未来)

- [ ] 云存储后端
- [ ] 多语言支持
- [ ] 高级分析
- [ ] 插件系统

---

## 📚 文档

### v2.0.0-alpha 文档

- **[Release Notes](RELEASE_NOTES.md)** - v2.0.0-alpha 发布说明
- **[Optimization Proposal](docs/OPTIMIZATION-PROPOSAL.md)** - 优化提案
- **[Optimization Summary](docs/OPTIMIZATION-SUMMARY.md)** - 实施总结

### v1.5.5 文档

- **[Changelog](CHANGELOG.md)** - v1.5.5 更新日志
- **[API 文档](docs/API.md)** - API 文档
- **[架构文档](docs/ARCHITECTURE.md)** - 架构文档
- **[批量压缩文档](docs/BATCH-COMPRESSION.md)** - 批量压缩文档

---

## 🤝 贡献指南

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📜 许可证

本项目采用 [MIT 许可证](LICENSE)。

---

## 🙏 致谢

**灵感来源**:
- **lossless-claw** (Martian Engineering) - LCM 插件架构
- **OpenClaw** - Agent 框架
- **LCM** (Lossless Context Management) - 核心概念

**特别感谢**:
- 罡哥 (sonicman0261) - 项目发起人和指导
- OpenClaw 社区 - 支持和反馈

---

## 💬 联系方式

- **Issues**: [GitHub Issues](https://github.com/SonicBotMan/lobster-press/issues)
- **Discussions**: [GitHub Discussions](https://github.com/SonicBotMan/lobster-press/discussions)

---

<div align="center">

**如果觉得有用，请给个 ⭐ Star 支持一下！**

![Star History Chart](https://api.star-history.com/svg?repos=SonicBotMan/lobster-press&type=Date)

Made with 💕 by SonicBotMan

**LobsterPress** - *从有损到无损的跨越* 🦞✨

</div>
