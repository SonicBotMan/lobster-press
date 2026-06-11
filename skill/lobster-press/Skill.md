---
name: lobster-press
description: LobsterPress 认知记忆系统 - DAG 压缩 + OpenClaw ContextEngine + MCP 服务器，让 AI 拥有长期记忆和智能压缩能力
---

# LobsterPress - OpenClaw 认知记忆系统

## 概述

LobsterPress 是一个为 OpenClaw 设计的**认知记忆系统**，通过 DAG（有向无环图）压缩、遗忘曲线和语义记忆技术，实现智能上下文管理。

**最新版本**: v5.0.3 (2026-05-30)

**核心特性：**
- **MemOS 4-Phase** — 向量嵌入 / 技能进化 / 多智能体 / 工程化
- **DAG 压缩** — 有向无环图结构，保留语义关系
- **C-HLR+ 遗忘曲线** — 自适应半衰期 + 复杂度因子
- **混合检索** — FTS5 + Vector → RRF → MMR → 时间衰减
- **ContextEngine 集成** — 自动监测上下文使用率，智能触发压缩
- **MCP 服务器** — 通过 MCP 协议提供 13 个工具

## 文档

文档位于仓库根目录 `docs/`：
- [API 文档](../../docs/API.md)
- [架构说明](../../docs/ARCHITECTURE.md)
- [配置指南](../../docs/CONFIGURATION.md)
- [OpenClaw 集成](../../docs/OPENCLAW-INTEGRATION.md)
- [性能基准](../../docs/BENCHMARK.md)
- [FAQ](../../docs/FAQ.md)
- [路线图](../../docs/ROADMAP.md)

## 脚本
## 脚本
工具脚本已移除（v5.0+ 全部功能已迁入 `src/`、`mcp_server/`、`tests/`，无遗留脚本）。
