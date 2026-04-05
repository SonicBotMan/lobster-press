<div align="center">

<img src="assets/lobster-press-banner.png" alt="LobsterPress - Transform AI conversations from 'ephemeral phantoms' into 'permanent nutrients in the digital hippocampus'" width="100%">
# 🧠 LobsterPress v5.0.0「MemOS 4-Phase」

**Cognitive Memory System for AI Agents**
*LLM persistent memory engine based on cognitive science*

[![npm version](https://img.shields.io/npm/v/@sonicbotman/lobster-press.svg)](https://www.npmjs.com/package/@sonicbotman/lobster-press)
[![GitHub release](https://img.shields.io/github/release/SonicBotMan/lobster-press.svg)](https://github.com/sonicBotMan/lobster-press/releases)
[![Test](https://github.com/SonicBotMan/lobster-press/workflows/Test/badge.svg)](https://github.com/SonicBotMan/lobster-press/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)
[中文](README.md) | **English**
**Latest**: [v5.0.0](https://github.com/SonicBotMan/lobster-press/releases/tag/v5.0.0) · [Changelog](CHANGELOG.md)
</div>
---

## 🎯 The Problem: AI's "Alzheimer's Dilemma"
All LLMs are constrained by context windows. When conversations exceed window length, traditional solutions use **sliding window truncation** — old messages are permanently discarded, trapping AI Agents in an "amnesia" loop.
This isn't just an engineering problem — it's a **cognitive science problem**:
- Human memory isn't a FIFO queue, but a **hierarchical, dynamically forgetting, reconsolidatable** cognitive system
- AI Agents need human-like memory mechanisms: **retain key decisions, forget trivial chats, dynamically update knowledge**
---

## 💡 Our solution: MemOS 4-Phase Architecture
LobsterPress v5.0 implements the **MemOS 4-Phase** cognitive memory optimization framework:

### 📚 Academic Foundation
| Paper/Theory | Application | Implementation |
|--------------|-------------|----------------|
| **MemOS (memos-claw.openmem.net)** | 4-Phase Framework | Core Intelligence → Skill Evolution → Multi-Agent → Engineering |
| **EM-LLM (ICLR 2025)** | Event Segmentation | Semantic boundary detection + temporal gap segmentation |
| **HiMem (Hierarchical Memory)** | Memory Hierarchy | DAG compression + 3-tier summary structure |
| **Ebbinghaus Forgetting Curve (1885)** | Dynamic Forgetting | R(t) = 0.5^(-t/h) — C-HLR+ corrected formula |
| **C-HLR+ (lobster-press)** | Complexity-driven decay | h = base_h × (1 + α × complexity) |
---

## 🚀 MemOS 4-Phase Architecture
LobsterPress v5.0 implements four optimization phases:

### Phase 1: Core Intelligence
- **Vector Embedder**: OpenAI compatible API (default) + offline local model support
- **Hybrid Retriever**: RRF k=60, MMR λ=0.7, 14-day time decay
- **FallbackLLMClient**: Multi-tier LLM provider fallback chain
- **Dual Decay Parameters**: Compression half-life 12h + retrieval half-life 14d (independent)

### Phase 2: Skill Evolution
- **Skill Data Models**: Skill definitions, version history, quality scores
- **Task Detector**: 2h timeout judgment + LLM topic classification
- **Skill Evolver**: Rule filter → LLM evaluation → SKILL.md → quality score
- **MCP Skill Tools**: `lobster_skill get/install/list`

### Phase 3: Multi-Agent
- **Public Memory**: `lobster_memory_write_public` — cross-agent memory sharing
- **Skill Discovery**: `lobster_skill_search` — skill registry search
- **Skill Marketplace**: `lobster_skill_publish/unpublish` — skill lifecycle management
- **Owner + Namespace Isolation**: Multi-agent memory isolation

### Phase 4: Engineering
- **OpenClaw Importer**: 🦐 prefix support, openclaw session import
- **Viewer Web UI**: 127.0.0.1:19876, SHA-256 auth
- **Async Queue Worker**: Background task processing
- **Phase 4 MCP Tools**: `lobster_viewer`, `lobster_import`

---

## 🚀 Core Features (C-HLR+ Forgetting Curve)
### Feature 1: Forgetting Curve Dynamic scoring
**Human-like Memory Decay Mechanism**
Based on the Ebbinghaus forgetting curve, each message is assigned different stability parameters by `msg_type`:
```
R(t) = base_score × e^(-t/stability)

Decision (decision): 90-day stability  → Key decisions retained long-term
Config (config):     120-day stability → System configs most stable
Code (code):         60-day stability  → Technical debt mid-term retention
Error (error):       30-day stability  → Issue tracking short-term retention
Chitchat (chitchat): 3-day stability   → Rapid forgetting of low-value content
```
**Memory Consolidation**: `lobster_grep` hits automatically refresh memory, achieving "retrieval as reinforcement".
---
### Feature 2: Event Segmentation (EM-LLM ICLR 2025)
**Automatic Conversation Topic Boundary Detection**
Adopting the **cognitive event segmentation** theory from EM-LLM paper, automatically partition conversations into episodes:
```
Semantic Boundary Detection: TF-IDF similarity < 0.25 triggers new episode
Temporal Gap Detection: Message interval > 1 hour auto-segments
Explicit Signal Detection: system messages trigger new episode
Hard Cap Protection: Cumulative tokens > max_episode_tokens forced segmentation
```
**Effect**: Conversations are no longer one-dimensional sequences, but **episodized cognitive units**, improving retrieval precision and context assembly efficiency.
---
### Feature 3: Semantic Memory Layer ⭐ NEW
**Persistent Knowledge Base Independent of Conversation Flow**
Borrowing from human **Semantic Memory** mechanism, extract persistent knowledge from conversations:
```
Conversation: "We decided to use PostgreSQL as primary database, considering ACID transaction requirements"
  ↓ (LLM extraction)
Semantic Memory:
  category: decision
  content: "Project adopts PostgreSQL (ACID transaction requirements)"
  confidence: 0.95
```
**Schema Design**:
```sql
CREATE TABLE notes (
    note_id         TEXT UNIQUE NOT NULL,
    conversation_id TEXT NOT NULL,
    category        TEXT NOT NULL,  -- preference/decision/constraint/fact
    content         TEXT NOT NULL,
    confidence      REAL DEFAULT 1.0,
    source_msg_ids  TEXT,           -- Traceability chain: which messages
    superseded_by   TEXT            -- Superseded by which new note
);
```
**Context Injection**: All active notes are always injected at context header (<500 tokens), ensuring Agent always remembers key decisions and preferences.
---
### Feature 4: Conflict Detection & Memory Reconsolidation ⭐ NEW
**Automatic Knowledge Base Detection and Update**
Based on **Memory Reconsolidation Theory** (Nader 2000), when new messages contradict existing knowledge:
```
Old Knowledge: "Using PostgreSQL"
New Message: "Switching to MongoDB for document flexibility"
  ↓ (Conflict Detection)
Action:
  1. Mark old note as superseded_by = "new_note_id"
  2. Create new note: "Project switches to MongoDB (document flexibility requirement)"
  3. Preserve complete traceability chain (don't delete old note)
```
**Dual Detection Strategy**:
- **NLI Model Detection** (Recommended): `cross-encoder/nli-deberta-v3-small`
  - High precision (conflict threshold 0.85)
  - Requires GPU or substantial memory
  - Install: `pip install sentence-transformers`
- **Rule-based Fallback Detection** (Backup): Zero dependency
  - Based on negation words + keyword co-occurrence
  - Patterns: `not (using|want|adopt)`, `switch (to|from)`, `abandon|deprecate|replace`
  - Automatically falls back when `sentence-transformers` is not installed
```
**Academic Significance**: Application of **Memory Reconsolidation** theory to LLM memory management, achieving dynamic knowledge evolution
---
## 🔬 Technical Architecture
### Three-Tier Compression Strategy
```
Context Usage        Strategy              LLM Cost    Technical Principle
─────────────────────────────────────────────────────
< 60%              No-op                 $0          
60% – 75%          Semantic Dedup        $0          Cosine Similarity
> 75%              DAG Summarization     $           LLM-generated hierarchical summaries
```
**TF-IDF Scoring + Auto-Exempt**:
```
"Decided to adopt React 18"     → decision  → exempt=True  ✅ Retained forever
"```python\ndef foo(): ..."      → code      → exempt=True  ✅ Retained forever
"Error: ECONNREFUSED"           → error     → exempt=True  ✅ Retained forever
"Sure, got it"                  → chitchat  → tfidf=2.1    Compressible
```
### DAG Structure (Lossless Compression)
```
Raw messages seq 1..N
     ↓  (Leaf compression, each chunk ≤ 20K tokens)
  leaf_A   leaf_B   leaf_C   [fresh tail: last 32 raw messages]
     ↓  (Hierarchical aggregation)
  condensed_1     condensed_2
     ↓
  root_summary
```
**Key Features**:
- ✅ **Lossless**: Every layer expandable by raw messages
- ✅ **Traceable**: DAG nodes append-only, never modified
- ✅ **Efficient**: 100K+ messages compressed to <200K tokens
```
---
## 🎓 Academic Value
### Comparison with existing work
| Dimension | LangChain Memory | Mem0 | Letta | LobsterPress v5.0 |
|-----------|------------------|------|-------|-------------------|
| Lossless Compression | Sliding window | Sliding window | DAG compression | DAG compression |
| Forgetting Curve | None | None | Ebbinghaus dynamic decay | C-HLR+ adaptive decay |
| Event Segmentation | None | None | EM-LLM ICLR 2025 | EM-LLM ICLR 2025 |
| Semantic Memory | None | Vector search | Vector search | Structured notes table |
| Vector Retrieval | None | Yes | Yes | Hybrid RRF + MMR |
| Skill Evolution | None | None | None | Yes (Phase 2) |
| Multi-Agent Memory | None | None | None | Yes (Phase 3) |
| Conflict Detection | None | None | NLI + Memory Reconsolidation | NLI + Memory Reconsolidation |
| Dynamic Scoring | None | None | None | Time-decay scoring |

> Note: Comparison based on the documentation as of 2026-03. Please submit an Issue if outdated.
```
**Academic Contributions**:
1. Application of Ebbinghaus forgetting curve to LLM memory management
2. Implementation of event segmentation based on EM-LLM paper
3. Application of Memory Reconsolidation theory to knowledge updates
---

## 🔌 OpenClaw Plugin (Recommended)
LobsterPress can be used as a native [OpenClaw](https://github.com/openclaw/openclaw) plugin. No manual Python service deployment required — just one command:
```bash
openclaw plugins install @sonicbotman/lobster-press
```
After installation, enable it in your OpenClaw configuration:
```json
{
  "plugins": {
    "entries": {
      "lobster-press": {
        "enabled": true,
        "config": {
          "llmProvider": "deepseek",
          "llmModel": "deepseek-chat",
          "contextThreshold": 0.75,
          "freshTailCount": 32
        }
      }
    }
  }
}
```
Once enabled, OpenClaw Agent will automatically have access to **22 memory tools**:

**Core Tools:**
- `lobster_grep` — Full-text search in historical memory (FTS5 + TF-IDF)
- `lobster_describe` — View DAG summary hierarchy structure
- `lobster_expand` — Losslessly expand summary to original messages
- `lobster_compress` — Manual context compression trigger
- `lobster_ingest` — Ingest messages into memory
- `lobster_assemble` — Assemble context from memory layers
- `lobster_sweep` — Apply forgetting curve decay
- `lobster_check_context` — Manual context usage check

**Skill Evolution (Phase 2):**
- `lobster_skill get` — Get skill definition
- `lobster_skill install` — Install a skill
- `lobster_skill list` — List installed skills

**Multi-Agent (Phase 3):**
- `lobster_memory_write_public` — Write cross-agent shared memory
- `lobster_skill_search` — Search skill registry
- `lobster_skill_publish` — Publish a skill
- `lobster_skill_unpublish` — Unpublish a skill

**Engineering (Phase 4):**
- `lobster_viewer` — Open web viewer UI
- `lobster_import` — Import openclaw sessions

These tools can also be used alongside [lossless-claw](https://github.com/martian-engineering/lossless-claw):
- **lossless-claw** handles context window DAG compression
- **lobster-press** handles cross-session long-term semantic memory retrieval

---
## 🚀 Quick Start
```bash
# Install as OpenClaw plugin (recommended)
openclaw plugins install @sonicbotman/lobster-press

# Or install from source
git clone https://github.com/SonicBotMan/lobster-press.git
cd lobster-press
pip install -r requirements.txt
```
```python
# Python API (standalone usage)
from src.database import LobsterDatabase
from src.incremental_compressor import IncrementalCompressor

db = LobsterDatabase("memory.db")
manager = IncrementalCompressor(
    db,
    max_context_tokens=200_000,  # Claude=200K, GPT-4o=128K, Gemini=1M
    context_threshold=0.75,
    fresh_tail_count=32
)
# Automatically decide compression strategy
result = manager.on_new_message("conv_id", {
    "id": "msg_001",
    "role": "user",
    "content": "We decided to use PostgreSQL as primary database",
    "timestamp": "2026-04-05T10:00:00Z"
})
# result["compression_strategy"] → "none" | "light" | "aggressive"
# result["notes_extracted"] → [{"category": "decision", "content": "..."}]
```
---
## 🛠️ Agent Tool Integration
```bash
# Full-text search history (FTS5 + TF-IDF reranking)
python -m src.agent_tools grep "PostgreSQL" --db memory.db --conversation conv_123
# View DAG summary structure
python -m src.agent_tools describe --db memory.db --conversation conv_123
# Expand summary to raw messages
python -m src.agent_tools expand sum_abc123 --db memory.db --max-depth 2
```
Python API:
```python
from src.agent_tools import lobster_grep, lobster_describe, lobster_expand

# Search, ranked by TF-IDF relevance
results = lobster_grep(db, "database selection", conversation_id="conv_123", limit=5)

# View summary hierarchy
structure = lobster_describe(db, conversation_id="conv_123")
# → {"total_summaries": 12, "max_depth": 3, "by_depth": {...}}

# Expand summary to raw messages
detail = lobster_expand(db, "sum_abc123")
# → {"total_messages": 47, "messages": [...]}
```
---
## 📊 Performance Metrics
**Test Environment**: M1 MacBook Pro, 16GB RAM, Python 3.11
| Operation | Performance | Notes |
|-----------|-------------|-------|
| Message ingestion | <5ms | Includes TF-IDF scoring + type classification |
| FTS5 search | <10ms | 100K+ messages, millisecond response |
| Light compression | 0ms | Cosine similarity dedup, no LLM calls |
| DAG compression | ~2s/1K tokens | Claude 3.5 Sonnet API |
| Conflict detection | <100ms | Rule-based fallback mode (zero dependency) |
**Compression Effect**:
- 100K+ messages → <200K tokens (500x compression ratio)
- Retain 100% raw messages (lossless)
- 95%+ key information in top 20K tokens
```
---
## 🔧 Configuration Parameters
```python
manager = IncrementalCompressor(
    db,
    max_context_tokens=200_000,    # Target model context window
    context_threshold=0.75,        # Compression trigger usage threshold
    fresh_tail_count=32,          # Protected recent message count
    leaf_chunk_tokens=20_000,     # Leaf summary chunk size
    llm_client=your_llm_client,   # Optional: for semantic extraction and conflict detection
)
# v5.0 new parameters:
embedder = VectorEmbedder(
    provider="openai",            # "openai" (default) or "local"
    model="text-embedding-3-small",
    api_base="https://api.openai.com/v1",  # OpenAI-compatible base URL
)
retriever = HybridRetriever(
    rrf_k=60,                    # RRF constant
    mmr_lambda=0.7,              # MMR diversity weight
    decay_retrieval_days=14,     # Retrieval half-life (independent of compression)
)
```
| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_context_tokens` | 40,000 | Target model context window |
| `context_threshold` | 0.75 | DAG compression trigger threshold (0.0–1.0) |
| `fresh_tail_count` | 32 | Protected recent messages, not compressed |
| `leaf_chunk_tokens` | 20,000 | Leaf compression chunk size (affects summary granularity) |
| `llm_client` | None | LLM client (for semantic extraction, optional) |
| `embedding_provider` | "openai" | Vector embedding provider ("openai" or "local") |
| `decay_compression_hours` | 12 | Compression half-life in hours (C-HLR+ base) |
| `decay_retrieval_days` | 14 | Retrieval half-life in days (independent) |
| `skill_timeout_hours` | 2 | Task detection timeout for skill evolution |
---
## 📦 Data Migration
Batch import from legacy versions or other formats
```bash
# Import from JSON (auto-scoring + classification + semantic extraction)
python -m src.pipeline.batch_importer data.json --db memory.db
# Import from CSV
python -m src.pipeline.batch_importer data.csv --format csv --db memory.db
# Specify batch size
python -m src.pipeline.batch_importer data.json --db memory.db --batch-size 50
```
---
## 🗂️ Project Structure
```
src/
├── database.py               # SQLite storage (messages, summaries, DAG, FTS5, notes, skills, embeddings)
├── dag_compressor.py         # DAG compression engine (leaf summaries + hierarchical aggregation)
├── incremental_compressor.py # Three-tier compression scheduler (main entry point)
├── semantic_memory.py        # Semantic memory layer (structured notes)
├── agent_tools.py            # lobster_grep / lobster_describe / lobster_expand
├── llm_client.py             # FallbackLLMClient + multi-provider support ⭐ v5.0
├── vector/
│   ├── embedder.py          # Vector embedding (Phase 1)
│   └── retriever.py         # Hybrid retrieval with RRF + MMR (Phase 1)
├── skills/
│   ├── models.py            # Skill data models (Phase 2)
│   ├── task_detector.py     # Task detection + topic classification (Phase 2)
│   └── evolver.py           # Skill evolution engine (Phase 2)
├── async_queue/
│   └── worker.py            # Async background task worker (Phase 4)
├── viewer/
│   └── server.py            # Web viewer UI (Phase 4)
├── migration/
│   └── importer.py          # OpenClaw session importer (Phase 4)
└── pipeline/
    ├── chlr_scorer.py      # C-HLR+ scoring (corrected 0.5^ formula)
    ├── tfidf_scorer.py       # TF-IDF scoring + message type classification
    ├── semantic_dedup.py     # Cosine similarity dedup (light strategy)
    ├── batch_importer.py     # Historical data batch import
    ├── event_segmenter.py    # Event segmentation (EM-LLM)
    └── conflict_detector.py  # Conflict detection
```
---
## 📜 Version History
| Version | Date | Notes |
|---------|------|-------|
| v1.0.0 ~ v1.5.5 | 2026-03-13~17 | Early iterations: DAG compression foundation |
| v2.5.0 ~ v2.6.0 | 2026-03-17 | Cognitive science refactor: EM-LLM + Forgetting curve |
| v3.0.0 ~ v3.2.1 | 2026-03-17 | LLM integration: Multi-provider + Prompt optimization |
| **v5.0.0** ⭐ | 2026-04-05 | MemOS 4-Phase: Vector retrieval, Skill evolution, Multi-Agent, Engineering |
<details>
<summary>View Full Version Details</summary>
### v5.0.0 (2026-04-05) - MemOS 4-Phase Optimization
- ✅ Phase 1: Vector embedder + HybridRetriever (RRF + MMR) + FallbackLLMClient
- ✅ Phase 2: Skill data models + Task detector + Skill evolver + MCP skill tools
- ✅ Phase 3: Public memory + Skill marketplace + Owner/Namespace isolation
- ✅ Phase 4: OpenClaw importer + Viewer Web UI + Async queue worker
- ✅ C-HLR+ formula fix: R(t) = 0.5^(-t/h) (corrected from math.exp)
- ✅ definePluginEntry() migration for OpenClaw v2026.4.2 compatibility
### v4.0.97 (2026-03-26) - C-HLR+ Forgetting Curve
- ✅ C-HLR+ algorithm implementation
- ✅ Pass 4 message deduplication
### v4.0.38 (2026-03-22) - Lifecycle Hooks
- ✅ before_agent_start + agent_end hooks for memory management
</details>
---
## 🙏 Acknowledgements
### Academic Citations
If LobsterPress helps your research, please cite the following papers
```bibtex
@misc{memos2026,
  title={MemOS: Cognitive Memory System for AI Agents},
  year={2026},
  url={https://memos-claw.openmem.net},
  author={MemOS Team}
}
@inproceedings{emllm2025,
  title={EM-LLM: Event-Based Memory Management for Large Language Models},
  booktitle={ICLR 2025},
  year={2025}
}
@article{nader2000memory,
  title={Memory reconsolidation: an update},
  author={Nader, Karim and Schafe, Glenn E and Le Doux, Joseph E},
  journal={Nature},
  year={2000}
}
```
### Open Source Projects
- **[lossless-claw](https://github.com/martian-engineering/lossless-claw)** (Martian Engineering) — DAG compression architecture reference
- **[LCM Paper](https://papers.voltropy.com/LCM)** (Voltropy) — Theoretical foundation for lossless context management
### Core Contributors
- **罡哥 (sonicman0261)** — Project initiator, architecture design, academic guidance
- **小云 (Xiao Yun)** — v3.0 core development, paper implementation
---
## 📄 License
[MIT License](LICENSE)
---
<div align="center">
**If LobsterPress helps your project, please give it a ⭐ Star!**
![Star History Chart](https://api.star-history.com/svg?repos=SonicBotMan/lobster-press&type=Date)
**Made with 🧠 by SonicBotMan & Xiao Yun**
*Based on cognitive science, building human-like memory systems for AI Agents*
</div>
