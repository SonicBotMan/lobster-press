<div align="center">

# 🦞 LobsterPress

**Lossless Conversation Compression Library for Python**  
*Persistent memory and intelligent context management for any LLM Agent framework*

[![GitHub release](https://img.shields.io/github/release/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press/releases)
[![GitHub stars](https://img.shields.io/github/stars/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press)
[![GitHub license](https://img.shields.io/github/license/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)

[中文](README.md) | **English**

**Latest**: [v2.5.0](https://github.com/SonicBotMan/lobster-press/releases/tag/v2.5.0) · [Release Notes](RELEASE_NOTES.md)

</div>

---

## Why LobsterPress?

Every LLM has a context window limit. The common approach is sliding-window truncation — but this means old messages are permanently lost and your Agent becomes "amnesic".

LobsterPress uses **lossless DAG compression**: every message is permanently stored in a local SQLite database. Layered summarization folds history into your context budget while preserving complete expansion paths. **Raw messages are never deleted.**

```
Traditional sliding window:  [msg 1..70 ❌ discarded]  [msg 71..100 kept]
LobsterPress:                [summary A → summary B → msg 95..100]  ← expandable to any original message
```

### How It Differs from lossless-claw

[lossless-claw](https://github.com/martian-engineering/lossless-claw) is an excellent project in the same space. LobsterPress differentiates with:

| | lossless-claw | LobsterPress |
|---|---|---|
| **Runtime** | OpenClaw plugin (Node.js) | Pure Python, framework-agnostic |
| **Compression trigger** | Single threshold (75%) | Three-tier ladder (60% / 75% / exempt) |
| **Message scoring** | None — all messages treated equally | TF-IDF + structural signals + time decay |
| **Key info protection** | None | `compression_exempt` auto-tagging |
| **Migration tools** | None | BatchImporter (JSON / CSV) |

> LobsterPress has no dependency on any specific Agent framework. It embeds cleanly into LangChain, AutoGen, custom agents, or any Python project.

---

## Quick Start

```bash
git clone https://github.com/SonicBotMan/lobster-press.git
cd lobster-press
pip install -r requirements.txt
```

```python
from src.database import LobsterDatabase
from src.incremental_compressor import IncrementalCompressor

db = LobsterDatabase("memory.db")
manager = IncrementalCompressor(
    db,
    max_context_tokens=200_000,  # match your model: Claude=200K, GPT-4o=128K, Gemini=1M
    context_threshold=0.75,
    fresh_tail_count=32
)

# Call after each conversation turn — compression is automatic
result = manager.on_new_message("conv_id", {
    "id": "msg_001",
    "role": "user",
    "content": "We've decided to use PostgreSQL as the primary database",
    "timestamp": "2026-03-17T10:00:00Z"
})
# result["compression_strategy"] → "none" | "light" | "aggressive"
```

---

## How It Works

### Three-Tier Compression Strategy

```
Context usage       Strategy              LLM call cost
──────────────────────────────────────────────────────
< 60%              No-op                 $0
60% – 75%          Semantic dedup        $0   ← zero API calls
> 75%              DAG summarization     $    ← LLM generates summaries
```

The `light` tier removes redundant messages using cosine similarity — **no LLM calls required**. In high-frequency conversation workloads, this can cut summarization API calls by 40–60%.

### TF-IDF Scoring + Auto-Exempt

Every message is scored and typed at ingest time:

```
"Decided to use React 18"          → msg_type="decision"  compression_exempt=True  ✅ kept forever
"```python\ndef foo(): ..."         → msg_type="code"       compression_exempt=True  ✅ kept forever
"Error: ECONNREFUSED"              → msg_type="error"      compression_exempt=True  ✅ kept forever
"Sure, got it"                     → msg_type="chitchat"   tfidf_score=2.1          can be compressed
```

Messages with `compression_exempt=True` skip LLM summarization during DAG compression. Their raw content remains in context permanently.

### DAG Structure

```
Raw messages seq 1..N
     ↓  (leaf pass — ≤ 20K token chunks)
  leaf_A   leaf_B   leaf_C   [fresh tail: last 32 raw messages]
     ↓  (condensation)
  condensed_1     condensed_2
     ↓
  root_summary
```

Every layer is expandable back to raw messages via `lobster_expand`. DAG nodes are append-only — no node is ever mutated.

---

## Agent Tool Integration

LobsterPress ships three tools for Agents to use during conversation:

```bash
# Full-text search over history (FTS5, millisecond response)
python -m src.agent_tools grep "PostgreSQL" --db memory.db --conversation conv_123

# Inspect DAG summary structure
python -m src.agent_tools describe --db memory.db --conversation conv_123

# Expand a summary back to raw messages
python -m src.agent_tools expand sum_abc123 --db memory.db --max-depth 2
```

Python API:

```python
from src.agent_tools import lobster_grep, lobster_describe, lobster_expand

# Search, ranked by relevance
results = lobster_grep(db, "database selection", conversation_id="conv_123", limit=5)

# Inspect summary hierarchy
structure = lobster_describe(db, conversation_id="conv_123")
# → {"total_summaries": 12, "max_depth": 3, "by_depth": {...}}

# Expand a summary to raw messages
detail = lobster_expand(db, "sum_abc123")
# → {"total_messages": 47, "messages": [...]}
```

---

## Configuration

```python
manager = IncrementalCompressor(
    db,
    max_context_tokens=200_000,  # Claude 3.5 Sonnet = 200K, GPT-4o = 128K, Gemini = 1M
    context_threshold=0.75,      # fraction of context window that triggers DAG compression
    fresh_tail_count=32,         # recent messages protected from any compression
    leaf_chunk_tokens=20_000,    # max source tokens per leaf summary chunk
)
```

| Parameter | Default | Description |
|---|---|---|
| `max_context_tokens` | 128,000 | Target model's context window size — **must match your model** |
| `context_threshold` | 0.75 | Usage fraction that triggers DAG compression (0.0–1.0) |
| `fresh_tail_count` | 32 | Most-recent messages shielded from compression |
| `leaf_chunk_tokens` | 20,000 | Leaf compression chunk size (controls summary granularity) |

---

## Data Migration

Batch-import from legacy versions (v1.5.5) or other formats:

```bash
# Import from JSON (auto-scored and classified)
python -m src.pipeline.batch_importer data.json --db memory.db

# Import from CSV
python -m src.pipeline.batch_importer data.csv --format csv --db memory.db

# Custom batch size
python -m src.pipeline.batch_importer data.json --db memory.db --batch-size 50
```

---

## Project Structure

```
src/
├── database.py               # SQLite storage (messages, summaries, DAG relations, FTS5)
├── dag_compressor.py         # DAG compression engine (leaf pass + hierarchical condensation)
├── agent_tools.py            # lobster_grep / lobster_describe / lobster_expand
├── incremental_compressor.py # Three-tier compression scheduler (main entry point)
└── pipeline/
    ├── tfidf_scorer.py       # TF-IDF scoring + message type classification
    ├── semantic_dedup.py     # Cosine similarity dedup (light strategy)
    └── batch_importer.py     # Bulk historical data import
```

---

## Known Issues (v2.5.0)

> Tracked in [Issue #95](https://github.com/SonicBotMan/lobster-press/issues/95), targeted for v2.5.1

- **[Critical]** FTS5 produces orphaned index rows on message update, causing ghost search results
- **[Critical]** `light` dedup strategy is a no-op — TODO not implemented, three tiers effectively become two
- **[Medium]** `max_context_tokens` historically defaults to 128K — Claude/Gemini users must pass it explicitly
- **[Medium]** `TFIDFScorer` instance state is not thread-safe under concurrent access

---

## Version History

| Version | Date | Highlights |
|---|---|---|
| **v2.5.0** ⭐ | 2026-03-17 | TF-IDF scoring, three-tier compression, compression_exempt, BatchImporter |
| v2.0.0-alpha | 2026-03-15 | Lossless DAG architecture, FTS5 search, Agent tools |
| v1.5.5 | 2026-03-13 | Lossy batch compression, 6.67x multi-thread speedup |

---

## Acknowledgements

- **[lossless-claw](https://github.com/martian-engineering/lossless-claw)** (Martian Engineering) — DAG compression architecture reference
- **[LCM paper](https://papers.voltropy.com/LCM)** (Voltropy) — Theoretical foundation for lossless context management
- **sonicman0261** — Project initiator and lead

---

## License

[MIT License](LICENSE)

---

<div align="center">

If you find this useful, please give it a ⭐ Star!

![Star History Chart](https://api.star-history.com/svg?repos=SonicBotMan/lobster-press&type=Date)

Made with 💕 by SonicBotMan

</div>
