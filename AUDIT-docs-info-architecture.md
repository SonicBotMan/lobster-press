# LobsterPress 文档信息架构诊断报告

> 审阅者视角：文档信息架构与叙事（资深技术文档工程师）
> 审阅对象：README.md（中文，783 行）、README_EN.md（英文，446 行）、CHANGELOG.md（457 行，27 个版本条目）
> 交叉验证：src/ 实际文件树、mcp_server/ 工具注册数（实测 17）、docs/ 目录现状
> 日期：2026-09-01（对应 v5.1.1）

---

## 0. 一句话总诊断

**README 不是在描述"v5.1.1 的 LobsterPress 是什么"，而是 v1→v5.1.1 每一版的沉积层**：安装教程占 45% 篇幅、当前态架构图自带版本标签和 Legacy 层、英文版停在 v5.0.0 且仍在宣传已删除的向量检索、README 内嵌的版本表已腐烂（同一版本重复 7 次）。读者必须自己脑内做三方 diff（中文 README × 英文 README × CHANGELOG）才能拼出产品现状——这是信息架构的失职，不是文笔问题。

---

## 1. 五维诊断

### D1 版本堆积病：确认，且是全文档的组织原则而非局部现象

文档按"每个版本往里加一段"叠层，读者无法直接读到当前态：

| 证据 | 位置 | 问题 |
|---|---|---|
| `### MemOS 4-Phase 架构（v5.0）` | R390 | "当前态"章节标题自带版本标签 |
| ASCII 图头 `LobsterPress v5.0「MemOS」` | R394 | 图声称当前架构，却标着 4 月的版本号 |
| `Legacy: CMV三遍无损压缩 + C-HLR+遗忘曲线 + R³Mem三层` | R416 | **架构图内部含 Legacy 层**——这张图画的是分层版本史，不是当前组件拓扑 |
| MCP 工具按 `v5.0 新工具 (Skill Evolution/Multi-Agent/Engineering)` 分组 | R469/475/484 | 工具以"哪个版本加的"分类，而非按功能；v5.1.1 没加新工具，所以工具清单 = 版本考古现场 |
| `### v5.0 Python API`；`v5.1.1: Viewer Web UI（v5.1.1 修复 setup() 遮蔽…）` | R540/552 | 代码示例里内嵌版本变更说明 |
| `LLM Fallback Chain (v5.0)` | R606 | 同上 |
| 英文版在旧版本条目上打补丁：`(v5.1.1: vector retriever removed — was dead code with random embeddings)`、`(async queue removed in v5.1.1)` | E396/399 | 在 v5.0.0 的历史条目里叠加 v5.1.1 的勘误——文本层积的直接物证 |
| 英文标题 `v5.0.0` vs 中文标题 `v5.1.1` | E4 vs R5 | 双语版本漂移，英文版整篇停在 4 月 |

**读者代价**：想知道"向量检索还在吗"，需要读 C26-28（Removed 段）+ 对照 R574-586（配置表仍列 `embed_provider/embed_endpoint/embed_model`，指向已删除的模块）+ 对照 E42-43（仍在宣传 Hybrid Retriever）——三个信源互相矛盾。

### D2 卖点与结构错位：头图承诺 vs 交付现实 vs 三处叙事互相打架

**头图承诺**（R3）："从阅后即焚的幻影进化为数字海马体中的永久养分"。
**现实**（C10-11，v5.1.1 P0）：压缩后只插 summary 不删原消息，"实测 12 条消息压缩后 context 反而 12→13 项"——直到 2026-09-01 修复前，核心承诺的机制本身是坏的。

**核心价值 5 条（R29-33）在 v5.1.0 时的真实状态**：
- 知识提取 → semantic 层是"空架子"，`memory_tier='semantic'` 全仓无写入方（C14），5.1.1 才接通
- 矛盾检测 → conflict_detector 规则反向误判（"替换掉老旧的数据库，顺便聊聊 React 生态"被判与"喜欢 React"矛盾，C19），5.1.1 才修复
- 中文全文搜索 → FTS5 unicode61 把整句中文当一个 token，永远 0 结果（C13），5.1.1 才修复
- 即：5 条卖点中 3 条在上一版是失效的，README 无任何状态标注

**删除后遗留的假卖点**（C26-28：`src/vector/`、`src/async_queue/`、5 个 v2 MCP 工具已删）：
- E42-43 仍宣传 "Vector Embedder / Hybrid Retriever: RRF k=60, MMR λ=0.7, 14d 时间衰减"
- E182 选型表仍写 "Vector Retrieval | Hybrid RRF + MMR"
- R584-586 配置表仍列 `embed_provider / embed_endpoint / embed_model`
- C27 亲口承认：NumpyOfflineEmbedder "用随机向量，检索结果是噪声"——即该卖点在存在的全部时间里都是假的

**三处叙事不一致**：
1. 架构图（R392-418）：讲 MemOS 4-Phase
2. 核心价值列表（R29-33）：讲压缩/遗忘/提取/矛盾/触发五件事
3. 学术基础表（R561-570）：8 篇理论，其中 2 篇标"arXiv ID 待作者核实"（R568-569）；且 bibtex 中 focus2025（R722）与 r3mem2025（R728）**共用同一个 arXiv:2502.15957**——C38 说 5.1.0 已移除撞 ID 的引用，但中文 bibtex 仍留雷

**MemOS 4-Phase 框架在删除后是否成立**：不成立。Phase 1 的实体内容（向量嵌入+混合检索）与 Phase 4 的 async queue 已删；4-Phase 现在描述的是 4 月的产品而非 9 月的产品。更糟的是 E31 自认该框架来自 MemOS（memos-claw.openmem.net）——**用同类竞品的概念框架名做自己的产品主标题**（R5 `LobsterPress v5.1.1「MemOS 4-Phase」`），等于在定位上为他人作嫁衣。

### D3 读者分层缺失：783 行平铺，且 docs/ 分层层"已存在但零链接"

**篇幅结构**（中文 README）：
- L1-19 头部；L23-34 核心价值（11 行）——真正讲"是什么"的只有约 30 行
- **L37-385 安装教程+配置向导+FAQ+高级配置 ≈ 349 行，占全文 45%**，其中 R199-251 是一段 52 行的虚构配置向导聊天实录（"您: 帮我配置 LobsterPress / AI: 欢迎使用…"）
- L437-490 MCP 工具参考、L493-555 Python API、L627-656 项目结构（维护者内容）、L660-682 版本史、L686-749 学术引用全文——四类读者内容平铺在同一层

**决定性发现**：`docs/` 目录已存在且含 12 个文档（ARCHITECTURE.md / API.md / FAQ.md / CONFIGURATION.md / OPENCLAW-INTEGRATION.md / MANUAL_MEMORY.md / ROADMAP.md / BATCH-COMPRESSION.md / BENCHMARK.md / EXAMPLES.md / CUSTOMIZATION.md / archive/），但 **grep 证实两份 README 对 `docs/` 的链接为 0 次**。内容分层的基础设施已经建好，却完全孤立；README 反而内嵌了自己的 FAQ（R255-331），与 docs/FAQ.md 双份维护。另外 C41 记录 docs/ 里 6 个文件带 v2 时代弃用 banner（"v2 示例在 v5 跑不通"）——拆分方案必须同时处理文档腐烂。

**中英安装指导互相矛盾**：E199 教用户 `openclaw plugins install @sonicbotman/lobster-press` 一行命令；R56 明确警告"**不要**使用 npm install -g，必须解压到 `~/.openclaw/extensions/lobster-press/`"。C202 证实 E 的写法正是 4.0.93 修掉的错误教程——英文版是中文版的老 fork，已严重分叉。

### D4 CHANGELOG vs README 版本史冗余：三套版本史，README 那套已腐烂

- CHANGELOG.md：27 个版本条目，Keep a Changelog 格式，权威且健康 → **应保留为唯一版本史**
- README.md L660-682 内嵌版本表：与 CHANGELOG 双维护，且已数据损坏——
  - `v4.0.25` 同一版本号重复出现 **7 次**（L670-680），日期从 03-13 排到 03-21，对应内容实为 CHANGELOG 中 4.0.26–4.0.34 一串不同条目
  - L669 `v4.0.41 Issue #174 专家反馈修复` 在 CHANGELOG 中**不存在**（C 的 #174 修复记在 4.0.36，L332-359）——两史冲突
- README_EN.md L385-407：第三套版本史（v1.0~v5.0 压缩版 + details 补丁注释）

**结论**：README 内版本表整表删除，只留 badge + 一行 "完整历史见 CHANGELOG.md"。README 版本表的存在价值为零、维护成本为负（每次发版三处同步，已同步失败）。

### D5 竞品定位缺失：中文版完全没有"和谁比"，英文版的对比表是减分项

- 中文 README **0 次提及** mem0 / letta / MemOS（grep 确认）——核心决策期读者（"我该不该用它替换我现在的 mem0"）读完 783 行仍无法回答
- 英文版有对比表（E174-188）但三重失格：
  1. 埋在 "Academic Value" 章节下，不是选型章节
  2. 数据失真："Vector Retrieval | Hybrid RRF + MMR"（已删）、"Sliding window" 概括 Mem0（与表内自身 "Mem0 Vector search" 行自相矛盾）
  3. 无核实日期承诺执行痕迹（E188 声称 "as of 2026-03"，其后再未更新）
- 讽刺的是产品**真实差异化**其实清楚：全本地 SQLite 零依赖、中文优先（trigram+中文复杂度加权）、OpenClaw 插件零部署、技能进化（从对话沉淀 SKILL.md，mem0/letta 均无）、notes+矛盾检测的知识重巩固——这些恰恰没被组织成选型叙事

---

## 2. 重构方案

### 2.1 目标目录树（含每文件一句话职责）

```
lobster-press/
├── README.md                       # 门面：是谁/为什么不同/10行装好/去哪深读，≤150 行，零版本号叙事
├── README_EN.md                    # 同构英文版：与中文同结构同版本号，禁止独立分叉（CI 校验章节锚点一致）
├── CHANGELOG.md                    # 唯一版本史（保留现状；仅修一处：补记 4.0.41 缺失或确认其不存在）
├── assets/                         # 现状保留
└── docs/                           # 深读层（重写 6 个 v2-banner 文件，旧文件移 docs/archive/）
    ├── installation.md             # OpenClaw 插件安装：前置表+6 步+验证命令+高级配置（吸收 R37-185、R345-384）
    ├── faq.md                      # 吸收 R255-331 FAQ 并合并现有 docs/FAQ.md，单份维护
    ├── architecture.md             # 当前态组件图：SQLite/DAG压缩/notes/技能/Viewer 拓扑，禁止版本标签与 Legacy 层
    ├── mcp-tools.md                # 17 工具参考，按 Read/Write/Manage/Skill/Multi-Agent/工程 分组（替换"v5.0 新"分组）
    ├── python-api.md               # Python API 参考（吸收 R493-555，剔除行内版本注释）
    ├── configuration.md            # 全部配置参数单一来源（删除 embed_* 三行；合并现 docs/CONFIGURATION.md）
    ├── skills-and-multi-agent.md   # 技能进化 + owner 隔离 + 公共记忆（现 4-Phase 中 Phase 2/3 的存活部分）
    ├── comparison.md               # mem0/letta/MemOS/LangChain 选型对比：能力矩阵+核实日期+"什么时候别选我"
    ├── academic-notes.md           # 学术基础+完整 bibtex（修 focus/r3mem 撞 ID；保留"待核实"标注）
    └── roadmap.md                  # 原 4-Phase 叙事改写为 roadmap：已删模块标 Removed，避免文档与代码互相撒谎
docs/archive/                       # v2 时代文档原样归档（目录已存在）
```

### 2.2 主 README 最小骨架（逐节职责 + 行数预算）

| # | 章节 | 职责一句话 | 预算 |
|---|---|---|---|
| 1 | 头部 | banner+一句话定位+badges+双语切换（保留 R1-19 骨架） | ~18 行 |
| 2 | 这是什么 | 问题 1 句 + 方案 1 句 + 现状 1 句（"全本地 SQLite、中文优先、无外部向量库"） | ~8 行 |
| 3 | 核心能力 | 5 条当前态能力，每条 1 行+docs 深读链接：DAG 无损可回溯 / 遗忘曲线 / 语义笔记+矛盾检测 / 技能进化 / 多 Agent 隔离 | ~10 行 |
| 4 | 快速安装 | 仅 OpenClaw 用户 3 步 10 行（创建目录→解压→配置），其余进 docs/installation.md | ~15 行 |
| 5 | 17 个 MCP 工具 | 一屏表：仅工具名+半句话，详情链 docs/mcp-tools.md | ~25 行 |
| 6 | 选型对比 | 3 行迷你矩阵（vs mem0/letta/MemOS 各一句"选它当…"），链 docs/comparison.md | ~10 行 |
| 7 | 文档索引 | docs/ 全链接表（本次重构后该章节才成立——当前为 0 链接） | ~12 行 |
| 8 | 版本 | badge+一行"完整历史见 CHANGELOG.md" | ~3 行 |
| 9 | 尾部 | 致谢一行+Star History | ~15 行 |
| | **合计** | | **≤120 行** |

**明确删除项**：52 行配置向导聊天实录（R199-251）、FAQ 全文（R255-331）、版本历史表（R660-682）、bibtex 全文（R692-749，留链接）、嵌入 embed_* 的配置表（R574-589 重写）。

### 2.3 迁移映射（旧 → 新）

| 旧位置（README.md） | 去向 |
|---|---|
| R3 头图 alt | 保留，但建议措辞与 P0 修复后的现实对齐 |
| R23-34 核心价值 | 主 README §3（去版本号） |
| R37-185 安装步骤 | docs/installation.md |
| R187-251 配置向导+聊天实录 | 删实录，向导一句话+docs/installation.md #配置向导 |
| R255-331 FAQ | docs/faq.md（合并现 docs/FAQ.md） |
| R345-384 高级配置+参数表 | docs/configuration.md |
| R388-434 架构+hooks | docs/architecture.md（重画无版本标签图） |
| R437-490 MCP 工具 | 主 README 一屏表 + docs/mcp-tools.md |
| R493-555 Python API | docs/python-api.md |
| R559-571 学术表 | docs/academic-notes.md |
| R574-589 配置参数 | docs/configuration.md（删 embed_*） |
| R592-610 LLM 提供商 | docs/configuration.md |
| R613-624 压缩策略 | docs/architecture.md |
| R627-656 项目结构 | docs/architecture.md 末尾 |
| R660-682 版本历史表 | **删除**，CHANGELOG.md 唯一归口 |
| R686-749 bibtex | docs/academic-notes.md |
| README_EN 全文 | 按 2.2 骨架重写对齐 v5.1.1 |

### 2.4 执行顺序

1. **止血 commit（半天）**：修英文版——E4 版本号→v5.1.1、删 E42-43 向量宣传、E182 对比表向量行、E199 错误安装命令、E219 "22 tools"→17、E396/399 补丁注释移入 CHANGELOG；中文版删 R584-586 embed_*、修 R722/728 撞 ID
2. 建骨架：重写主 README 至 ≤120 行；建 docs/ 六个新文件；6 个 banner 文件移 archive/
3. 双语一致性 CI：校验两 README 标题版本号一致、章节锚点集合一致、`docs/` 链接无 404

---

## 3. TOP 3

1. **先修诚实性，再修结构**（最高优先级）：英文 README 此刻仍在宣传已删除且"检索结果是噪声"的向量检索（E42-43、E182）、给出 4.0.93 就修掉的错误安装命令（E199）、标着 v5.0.0——这不是文风问题，是产品对外说谎；一次 commit 对齐双语到 v5.1.1 现实。
2. **README 瘦身到 ≤120 行骨架 + 激活 docs/ 分层**：安装/FAQ/工具参考/学术全部下沉 docs/（半数文件已存在，只是零链接）；主 README 只回答"是什么/装/去哪读"。45% 的安装内容是决策期读者的最大噪音。
3. **版本史唯一归口 CHANGELOG，全文档去版本号叙事**：删 R660-682 腐烂表（v4.0.25×7、幽灵 v4.0.41）；"v5.0 新工具/（v5.0）/Legacy"等标签全部改为功能命名；当前态架构图重画（无 Legacy 层）；MemOS 4-Phase 从主标题降级为 docs/roadmap.md 中的一段演进史。

---

## 附：重定位一句话（供卖点重写参考）

> LobsterPress：**跑在本地的中文优先 Agent 记忆系统**——SQLite 单文件、零向量库依赖；DAG 无损压缩永远可回溯原始消息；语义笔记 + 矛盾检测让知识自我更正；独有技能进化，把对话沉淀成可复用的 SKILL.md。OpenClaw 插件即装即用。
（对比叙事：mem0=托管向量记忆服务、letta=有状态 Agent 运行时、MemOS=记忆操作系统框架；LobsterPress=嵌入式本地记忆引擎，选它当你不想要云依赖且主力场景是中文。）
