---
name: lobster-press
description: LobsterPress 智能上下文压缩系统 - 零成本压缩会话上下文，TF-IDF评分+语义去重+提取式摘要，让 AI 记忆永不溢出
---

# LobsterPress - OpenClaw 智能上下文压缩

## 概述

LobsterPress 是一个为 OpenClaw 设计的智能上下文压缩系统，通过 TF-IDF 三层评分、语义去重和提取式摘要技术，实现**零 API 成本**的会话压缩。

**核心特性：**
- **零成本压缩** - local 模式下 API 调用为 0，压缩成本 $0.00
- **质量守卫** - 自动检测压缩质量，不达标时自动回滚
- **Token 净收益** - 短会话 +500，中会话 +3,500，长会话 +8,000
- **无损压缩** - 提取式摘要，不生成新 token，不引入 AI 幻觉

## 使用场景

当用户提到以下关键词时自动触发：
- "压缩会话"、"压缩上下文"
- "Token 不够了"、"上下文太长"
- "会话压缩"、"智能压缩"
- "清理对话"、"优化上下文"

## 快速开始

### 安装依赖

```bash
cd ~/.openclaw/workspace/skills/lobster-press/scripts
pip install -r requirements.txt
```

### 基本用法

```bash
# 压缩当前会话（local 模式，零成本）
python3 scripts/lobster_press_v120.py --mode local

# 查看压缩预览（不实际执行）
python3 scripts/lobster_press_v120.py --dry-run

# 指定压缩强度
python3 scripts/lobster_press_v120.py --strategy medium
```

## 压缩模式

| 模式 | API 成本 | 压缩效果 | 适用场景 |
|------|---------|---------|---------|
| local | $0.00 | 40-60% | 日常使用，快速压缩 |
| hybrid | 按需 | 50-70% | 需要更高质量 |
| api | 正常 | 60-80% | 最高质量要求 |

## 压缩策略

### TF-IDF 三层叠加评分

1. **Layer 1 - 词汇稀有度**：TF-IDF 分数，稀有词权重高
2. **Layer 2 - 结构性信号**：决策、错误、代码块等规则加分
3. **Layer 3 - 时间衰减**：近期消息权重更高

### 语义去重

- 余弦相似度 > 0.82 视为重复
- 保留重要性更高的消息
- 避免信息冗余

### 质量守卫（v1.2.1）

压缩后自动检查：
- `decision_preserved` - 关键决策是否保留
- `config_intact` - 配置信息是否完整
- `context_coherent` - 上下文是否连贯

质量不达标时**自动回滚**到原始会话。

## 性能基准

| 上下文大小 | 旧版净收益 | v1.2.1 净收益 | 提升 |
|-----------|----------|--------------|------|
| 5k tokens | -350 | +500 | +850 |
| 15k tokens | +2,150 | +3,500 | +1,350 |
| 30k tokens | +5,900 | +8,000 | +2,100 |

## 目录结构

```
lobster-press/
├── SKILL.md                    # 本文件
├── scripts/
│   ├── lobster_press_v120.py   # 主压缩脚本
│   ├── compression_validator.py # 质量守卫
│   ├── tfidf_scorer.py         # TF-IDF 评分
│   ├── semantic_dedup.py       # 语义去重
│   ├── extractive_summarizer.py # 提取式摘要
│   └── requirements.txt        # Python 依赖
└── docs/
    ├── README.md               # 完整文档
    ├── BENCHMARK.md            # 性能基准
    ├── ROADMAP.md              # 开发路线图
    └── OPENCLAW-INTEGRATION.md # 集成指南
```

## 配置选项

在 `~/.openclaw/openclaw.json` 中配置：

```json
{
  "lobsterPress": {
    "mode": "local",
    "strategy": "balanced",
    "qualityGuard": true,
    "autoRollback": true
  }
}
```

## 示例

### 示例 1：日常压缩

```bash
# 用户：压缩一下会话
# 触发 lobster-press skill

python3 scripts/lobster_press_v120.py --mode local
```

### 示例 2：深度压缩

```bash
# 用户：上下文太长了，深度压缩
python3 scripts/lobster_press_v120.py --strategy heavy --mode hybrid
```

### 示例 3：预览模式

```bash
# 用户：看看压缩后能省多少 token
python3 scripts/lobster_press_v120.py --dry-run --stats
```

## 依赖说明

**Python 版本**：3.8+

**核心依赖**：
- numpy >= 1.20.0
- scikit-learn >= 0.24.0

安装：
```bash
pip install -r scripts/requirements.txt
```

## 版本历史

### v1.2.1 (2026-03-10)
- 新增质量守卫（自动回滚）
- 新增架构说明文档
- 优化压缩校验器

### v1.2.0 (2026-03-10)
- 零成本本地压缩
- TF-IDF 三层评分
- 语义去重
- 提取式摘要

## 常见问题

**Q: 压缩会丢失重要信息吗？**
A: 不会。质量守卫会检查关键决策、配置信息是否保留，不达标自动回滚。

**Q: local 模式真的零成本吗？**
A: 是的。local 模式完全在本地处理，不调用任何 API。

**Q: 压缩后能省多少 token？**
A: 根据会话长度，净收益从 +500 到 +8,000 不等。

## 技术支持

- GitHub: https://github.com/SonicBotMan/lobster-press
- Issues: https://github.com/SonicBotMan/lobster-press/issues
- 文档: docs/ 目录

---

**License**: MIT
**Version**: v1.2.1
**Author**: LobsterPress Team
