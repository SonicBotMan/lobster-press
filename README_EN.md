<div align="center">

<img src="assets/lobster-press-banner.png" alt="LobsterPress — a local-first, Chinese-native cognitive memory system for AI agents" width="100%">

# 🧠 LobsterPress

**Cognitive Memory System for AI Agents**
*Local-first permanent memory for LLMs: single-file SQLite, zero vector-DB dependency*

[![npm version](https://img.shields.io/npm/v/@sonicbotman/lobster-press.svg)](https://www.npmjs.com/package/@sonicbotman/lobster-press)
[![GitHub release](https://img.shields.io/github/release/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press/releases)
[![Test](https://github.com/SonicBotMan/lobster-press/workflows/Test/badge.svg)](https://github.com/SonicBotMan/lobster-press/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)

[中文](README.md) | **English**

**Current version**: [v5.1.1](https://github.com/SonicBotMan/lobster-press/releases) · [Full changelog](CHANGELOG.md)

</div>

---

## What is this

Every LLM hits the context-window wall, and sliding-window truncation throws old conversations away forever. LobsterPress stores every agent turn in a local SQLite file and manages memory with cognitive-science strategies (lossless DAG compression + forgetting curves + semantic notes) — original messages are never deleted, and every summary is traceable.

**One-line positioning**: a local-first, Chinese-native memory engine for agents. Choose it when you don't want cloud or vector-DB dependencies and your primary language is Chinese.

## Core capabilities

| Capability | What it does | Deep dive |
|------|------|------|
| 🗜️ Lossless DAG compression | Layered summaries shrink context; 100% of original messages stay traceable | [Architecture](docs/ARCHITECTURE.md) |
| ⏳ Forgetting curve | C-HLR+ dual half-life: key decisions persist, small talk decays | [Architecture](docs/ARCHITECTURE.md) |
| 📝 Semantic notes + conflict detection | Structured knowledge extracted from conversations; new claims that contradict old notes are flagged | [API](docs/API.md) |
| 🔍 Chinese-native full-text search | FTS5 trigram tokenizer; ≥3-char queries hit the index, shorter ones fall back to LIKE | [API](docs/API.md) |
| 🧬 Skill evolution | Distills recurring task conversations into reusable SKILL.md files | [Manual memory](docs/MANUAL_MEMORY.md) |
| 👥 Multi-agent isolation | owner/namespace isolation + shared public memory | [Architecture](docs/ARCHITECTURE.md) |

## Quick install (OpenClaw plugin)

```bash
# 1. Create the plugin directory (required — do NOT npm install -g)
mkdir -p ~/.openclaw/extensions/lobster-press && cd $_
# 2. Download & extract
npm pack @sonicbotman/lobster-press@latest && tar -xzf *.tgz --strip-components=1 && rm *.tgz
# 3. Restart the Gateway, then ask your agent to "help me configure LobsterPress"
```

Prerequisites: OpenClaw Gateway ≥ 2026.4.2, Node.js 18+, Python 3.10+. Verify: ask your agent to "report lobster_status".
Full walkthrough / troubleshooting → **[OpenClaw Integration](docs/OPENCLAW-INTEGRATION.md)** · **[FAQ](docs/FAQ.md)**

## MCP tools (17)

| Layer | Tools |
|----|------|
| Read | `lobster_grep` full-text search · `lobster_describe` summary tree · `lobster_expand` expand to raw messages · `lobster_status` health report |
| Write | `lobster_ingest` message ingestion · `lobster_compress` trigger compression · `lobster_correct` corrections |
| Manage | `lobster_assemble` context assembly · `lobster_sweep` decay marking · `lobster_prune` cleanup |
| Skills / multi-agent | `lobster_skill` · `lobster_skill_search` · `lobster_skill_publish` · `lobster_skill_unpublish` · `lobster_memory_write_public` |
| Engineering | `lobster_viewer` web UI · `lobster_import` OpenClaw migration |

Full signatures and return shapes → [docs/API.md](docs/API.md). The OpenClaw plugin layer additionally registers two TS tools: `lobster_configure` / `lobster_check_context`.

## vs. mem0 / letta

| | LobsterPress | mem0 | letta |
|---|---|---|---|
| Form | Local embedded engine (single SQLite file) | Managed vector memory service | Stateful agent runtime |
| Chinese search | ✅ native trigram | embedding-dependent | embedding-dependent |
| Unique capability | Skill evolution + conflict detection | Mature ecosystem | Long-running agents |

Verified 2026-09-01; full comparison and "when NOT to choose this" → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Documentation

| Doc | Contents |
|------|------|
| [docs/OPENCLAW-INTEGRATION.md](docs/OPENCLAW-INTEGRATION.md) | OpenClaw install, config wizard, advanced config |
| [docs/FAQ.md](docs/FAQ.md) | FAQ & troubleshooting |
| [docs/API.md](docs/API.md) | 17 MCP tools + Python API reference |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Current-state architecture, compression/forgetting algorithms, comparison |
| [docs/MANUAL_MEMORY.md](docs/MANUAL_MEMORY.md) | Manual memory management guide |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Evolution history & roadmap (incl. v5.1.1 removals) |
| [CHANGELOG.md](CHANGELOG.md) | Full version history |

## License

MIT
