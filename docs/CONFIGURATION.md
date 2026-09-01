# 配置参考（v5.1.1）

> 本表是配置参数的**唯一事实源**，全部经代码核对（index.ts 白名单 / src/incremental_compressor.py / src/llm_client.py）。v5.1.1 起不再存在的参数（`embed_provider` / `embed_endpoint` / `embed_model` / `focus_interval` / `urgent_threshold` / `retrieval_half_life_days` / `compression_half_life_hours`）已删除——向量检索与队列模块随 v5.1.1 移除，三策略触发阈值为内置常量不可配。

## OpenClaw 插件配置（index.ts 校验白名单）

对 Agent 说「帮我配置 LobsterPress」或在插件配置中设置：

| 参数 | 默认 | 说明 |
|------|------|------|
| `dbPath` | `~/.openclaw/lobster.db` | SQLite 数据库路径 |
| `contextThreshold` | `0.75` | 上下文使用率压缩阈值（0.60/0.75 策略分界的上限） |
| `maxContextTokens` | `128000` | 上下文 token 上限（Claude 200K / Gemini 1M 可调） |
| `llmProvider` | `mock` | LLM 提供商，见下表 |
| `llmModel` | — | 模型名 |
| `llmApiKey` | — | API 密钥 |
| `namespace` | `default` | 记忆命名空间 |
| `registerAsDefault` | — | 注册为默认记忆插件 |
| `freshTailCount` | `32` | ⚠️ v5.1.1 已知问题：TS 层校验此参数但**未传给 Python 进程**，修改不生效（Python 侧固定 32），修复跟踪见 ROADMAP |

## 环境变量（src/llm_client.py 读取）

| 变量 | 说明 |
|------|------|
| `LOBSTER_LLM_PROVIDER` | 提供商（缺省 mock） |
| `LOBSTER_LLM_API_KEY` | API 密钥 |
| `LOBSTER_LLM_MODEL` | 模型名 |
| `LOBSTER_LLM_SKILL_PROVIDER` / `_API_KEY` / `_MODEL` | 技能进化专用模型（可选） |
| `LOBSTER_LLM_SUMMARY_PROVIDER` / `_API_KEY` / `_MODEL` | 摘要专用模型（可选） |
| `BAIDU_SECRET_KEY` | 选 `baidu` 提供商时必需（缺失时静默 fallback，勿只配 LOBSTER_LLM_API_KEY） |

## LLM 提供商（8 个）

`qwen` · `deepseek` · `moonshot` · `zhipu` · `minimax` · `openai` · `anthropic` · `baidu`

> 全部提供商均可用 `mock` 降级运行（无 LLM 时核心压缩/检索功能不受影响，仅知识提取/摘要降质）。

## Python 侧构造参数

见 [PYTHON-API.md](PYTHON-API.md#构造参数默认值--v511-代码默认)（`IncrementalCompressor` 一节）。

## 历史文档

v2 时代的部署脚本配置方式已归档至 [archive/](archive/)（不适用于 v5+）。
