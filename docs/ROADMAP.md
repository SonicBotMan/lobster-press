# 演进史与路线（Roadmap）

> 主 README 与架构文档只描述当前态。本文回答"为什么现在是这样"——每个版本的取舍与移除决策。逐版细节以 [CHANGELOG.md](../CHANGELOG.md) 为准。

## 演进脉络

| 阶段 | 时间 | 关键变化 |
|------|------|----------|
| v1–v3 | 2026 上半年 | 基础记忆层：SQLite 存储、FTS 检索、MCP 工具化 |
| v4.x | 2026-03 | 记忆优先级排序（semantic > episodic > working）、ESM 兼容、Issue 修复潮 |
| v5.0 | 2026-04 | 技能进化、多 Agent 隔离、Viewer、OpenClaw 插件化 |
| v5.1.1 | 2026-09-01 | 全面审计修复 + 死代码清理（见下） |

## v5.1.1 审计：核心承诺修复

v5.0 宣传的 5 条核心卖点中 3 条经独立审计发现实际失效，v5.1.1 修复：

1. **压缩不缩容**：压缩只插入摘要不删除原消息展示位，上下文 12→13 反增 → 修复为真实缩容
2. **中文搜索永远 0 结果**：unicode61 分词器把整句中文当一个 token → 换 trigram
3. **语义记忆空架子**：`memory_tier='semantic'` 无写入方 → 接通 SemanticMemory notes
4. 另修复：condensed 摘要无限重压缩、矛盾检测反向误判、viewer 全请求 500

## v5.1.1 移除项（及原因）

| 移除 | 原因 |
|------|------|
| `src/vector/`（VectorEmbedder + HybridRetriever） | 从未接入 MCP/插件主链路；离线 embedder 产生随机向量，检索结果是噪声。宣传的 RRF/MMR 混合检索在存在期间即不可用 |
| `src/async_queue/` | 0 生产调用方 |
| 5 个 v2 压缩链 MCP 工具 | 依赖上述死代码 |

> 曾把向量检索列为 Phase 1 卖点，诚实的结论是：在 SQLite 场景下 trigram 全文检索已覆盖实际需求，向量层若有真实需求将以可选扩展形式回归（见下）。

## 移除后的框架说明

v5.0 的 "MemOS 4-Phase" 框架名退役（Phase 1/4 的实体已删，且名称借自同类项目）。当前架构不再使用代号框架，直接按组件描述——见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 待办 / 已知问题

- [ ] `freshTailCount` 配置未传给 Python 进程（改配置不生效，见 [CONFIGURATION.md](CONFIGURATION.md) 标注）
- [ ] 压缩缩容已作用于 context_items 视图；`lobster_assemble` 的 working 层仍读 `messages.memory_tier`，token 缩减尚未完全传导到组装链路
- [ ] `lobster_expand` 对不存在的 summary_id 静默返回空结果（不报错）
- [ ] npm 包内混入 `__pycache__/*.pyc`（含已删模块残留），待加 pack 清理

## 长期方向

- 可选向量扩展（真实 embedding 后端接入后按需启用）
- 双语文档一致性自动校验（章节锚点对齐）
- v2 时代遗留文档全部清出 docs/archive/
