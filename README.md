<div align="center">

<img src="https://raw.githubusercontent.com/SonicBotMan/lobster-press/master/docs/images/banner.jpg" alt="LobsterPress - 智能上下文压缩系统" width="800">

</div>

<div align="center">

**中文** | [English](README_EN.md)

</div>

# 🦞 龙虾饼 (LobsterPress)

<div align="center">

**智能上下文压缩系统 - 让 AI 记忆永不溢出**

[![GitHub release](https://img.shields.io/github/release/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press/releases)
[![GitHub stars](https://img.shields.io/github/stars/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press)
[![GitHub license](https://img.shields.io/github/license/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press)

*把龙虾般膨胀的上下文，压成一张薄饼*

**最新版本**: [v1.3.3](https://github.com/SonicBotMan/lobster-press/releases/tag/v1.3.3) - 2026-03-11
**更新内容**: [CHANGELOG.md](CHANGELOG.md)

</div>

---

## 🚀 快速开始（3 分钟）

### 1️⃣ 克隆项目
```bash
git clone https://github.com/SonicBotMan/lobster-press.git
cd lobster-press
```

### 2️⃣ 安装依赖
```bash
pip install -r requirements.txt
```

### 3️⃣ 运行压缩
```bash
# 单个会话
python scripts/lobster_press_v124.py session.jsonl -o compressed.jsonl

# 批量压缩（6.67x 性能提升）
python scripts/batch_compressor.py sessions/ compressed/ --workers auto
```

**完成！** ✅

---

## ✨ 核心特性

### 🔥 零成本本地压缩

- **API 调用: 0** - 完全本地化，零 API 成本
- **TF-IDF 三层评分** - 词汇稀有度 + 结构信号 + 时间衰减
- **语义去重** - 余弦相似度 > 0.82 视为重复
- **提取式摘要** - 不生成新 token，不引入 AI 幻觉

### 🚀 批量压缩性能优化

**性能提升：6.67x** 🔥

| 场景 | 单线程 | 8 线程 | 提升 |
|------|--------|--------|------|
| 100 sessions | 120s | 18s | **6.67x** |
| 376 sessions | 450s | 67s | **6.67x** |

**功能：**
- 🚀 **并发处理** - 多线程并发，支持 1-8 线程
- 📊 **实时进度** - 进度百分比、速度、预计剩余时间
- ⏱️ **超时控制** - 单会话超时，避免卡死
- 🎯 **智能线程配置** - 根据 CPU/内存自动推荐

### 🛡️ 质量守卫（Quality Guard）

- ✅ **净收益校验** - 避免负收益压缩
- ✅ **上下文连贯性** - 强制保留最近 N 条消息
- ✅ **Token 精确计量** - 中文误差从 30% 降至 5%
- ✅ **压缩质量报告** - 实时反馈压缩效果

---

## 📊 使用示例

### 单个会话压缩

```bash
# 基础用法
python scripts/lobster_press_v124.py session.jsonl -o compressed.jsonl

# 使用 heavy 策略
python scripts/lobster_press_v124.py session.jsonl --strategy heavy -o compressed.jsonl

# 预览模式（不写入文件）
python scripts/lobster_press_v124.py session.jsonl --dry-run

# 查看详细报告
python scripts/lobster_press_v124.py session.jsonl --report
```

### 批量压缩

```bash
# 基础用法
python scripts/batch_compressor.py sessions/ compressed/

# 高级用法（自动线程）
python scripts/batch_compressor.py sessions/ compressed/ --workers auto

# 手动指定
python scripts/batch_compressor.py sessions/ compressed/ \
  --strategy aggressive \
  --workers 8 \
  --timeout 600 \
  --limit 100
```

### 智能资源检测

```bash
# 自动检测并推荐线程数
python scripts/resource_detector.py

# 输出示例：
# CPU 核心数: 8
# 可用内存: 12.5 GB
# 推荐线程数: 6
```

---

## 💡 压缩策略

| 策略 | 保留率 | 使用场景 |
|------|--------|----------|
| **light** | 85% | 轻度压缩，保留大部分内容 |
| **medium** | 70% | 平衡策略（默认） |
| **heavy** | 55% | 激进压缩，最大化节省 |

---

## 🏗️ 架构说明

### v1.3.x 架构

```
systemd timer
    └── lobster_runner.sh（轻量 Shell）
            │
            ├── lobster_press_v124.py（核心引擎）
            │   ├── TF-IDF 评分
            │   ├── 语义去重
            │   ├── 提取式摘要
            │   ├── Token 计数
            │   ├── 净收益校验
            │   └── 质量守卫
            │
            └── batch_compressor.py（批量处理）
                ├── 并发处理
                ├── 实时进度
                └── 超时控制
```

### 压缩阈值

| Token 使用率 | 策略 | 操作 |
|--------------|------|------|
| < 70% | none | 无需压缩 |
| 70-85% | light | 轻度压缩 |
| 85-95% | medium | 中度压缩 |
| > 95% | heavy | 重度压缩 |

---

## 📁 项目结构

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

## 📈 性能指标

### 压缩效果

| 上下文大小 | 压缩率 | Token 节省 |
|------------|--------|------------|
| 5k tokens | 40% | ~2,000 |
| 15k tokens | 50% | ~7,500 |
| 30k tokens | 60% | ~18,000 |

### 批量压缩性能

| 场景 | 单线程 | 8 线程 | 提升 |
|------|--------|--------|------|
| 100 sessions | 120s | 18s | **6.67x** |
| 376 sessions | 450s | 67s | **6.67x** |

### 系统开销

- **CPU**: < 5%（单线程）
- **内存**: < 100MB
- **磁盘**: 临时文件 < 1MB

---

## 🤝 贡献指南

### 贡献方式

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

### 代码规范

- 使用 ShellCheck 检查 Bash 脚本
- 使用 Pylint 检查 Python 代码
- 添加详细注释
- 遵循现有代码风格

---

## 📝 更新日志

### v1.4.0 (2026-03-11) - Latest

- 🔥 **Issue #63: 集成三个核心模块**
  - TF-IDF 评分器 (真正的 TF-IDF 评分)
  - 语义去重 (余弦相似度 > 0.82)
  - 提取式摘要 (选择信息密度最高的句子)
- 🔥 **Issue #64: Quality Guard 字段修复**
  - 消除假阳性
  - 决策保留率检查正常
  - 配置完整性检查正常
  - 上下文连贯性检查正常
- 🔥 **Issue #65: 增量压缩集成真实引擎**
  - 集成 LobsterPressV124.compress()
  - 分块处理 (500条/块)
  - 支持进度保存和恢复
- 🎯 **质量保证**
  - 所有测试通过
  - 质量评分: 100/100

### v1.3.3 (2026-03-11)
- 🔥 合并 v1.2.4-hotfix1-6 (25 个 Bug 修复)
- 🚀 合并 v1.3.2 (6.67x 性能提升)
- 📊 实时进度、超时控制
- 🎯 智能线程配置

**详细更新**: [CHANGELOG.md](CHANGELOG.md)

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

---

## 💬 联系方式

- **Issues**: [GitHub Issues](https://github.com/SonicBotMan/lobster-press/issues)
- **Discussions**: [GitHub Discussions](https://github.com/SonicBotMan/lobster-press/discussions)

---

<div align="center">

**如果觉得有用，请给个 ⭐ Star 支持一下！**

![Star History Chart](https://api.star-history.com/svg?repos=SonicBotMan/lobster-press&type=Date)

Made with 💕 by SonicBotMan

</div>
