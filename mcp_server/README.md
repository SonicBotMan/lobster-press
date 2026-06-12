# LobsterPress MCP Server

> **For OpenClaw users**: prefer the [plugin install path](../README.md#-openclaw-插件推荐) — this file documents running the MCP server standalone (Claude Desktop, Cursor, custom clients).

The MCP server exposes **17 tools** over JSON-RPC on stdin/stdout. Launch with:

```bash
python3 -m mcp_server.lobster_mcp_server --db ~/.openclaw/lobster.db --namespace default
```

## Tools (17)

### Read layer

+- `lobster_grep` — FTS5 + TF-IDF search (`query`, optional `conversation_id`, `limit`)
+- `lobster_describe` — DAG summary structure (`summary_id` or `conversation_id`)
+- `lobster_expand` — expand summary to original messages (`summary_id`, `max_depth`)
+- `lobster_status` — system health report (no args)

### Write layer

+- `lobster_ingest` — write raw messages (`conversation_id`, `messages[]`)
+- `lobster_compress` — trigger DAG compression (`conversation_id`, `token_budget`)
+- `lobster_correct` — correct memory content (`target_type`, `target_id`, `correction_type`)

### Manage layer

+- `lobster_sweep` — mark decayed messages (`conversation_id`)
+- `lobster_assemble` — assemble 3-layer context (`conversation_id`, `token_budget`)
+- `lobster_prune` — delete decayed messages (`conversation_id`)

### Skills (v5.0)

+- `lobster_skill` — get/install/list (action selector: `action`, `skill_id` or `conversation_id`)
+- `lobster_memory_write_public` — write public memory (`content`)
+- `lobster_skill_search` — search skills across scopes (`query`, `scope`)
+- `lobster_skill_publish` — publish skill to public (`skill_id`)
+- `lobster_skill_unpublish` — privatize skill (`skill_id`)

### Engineering (v5.0)

+- `lobster_viewer` — open Web UI (`action`, `port`)
+- `lobster_import` — import OpenClaw memory (`action`)

## Protocol

JSON-RPC over stdin/stdout. On startup the server emits:

```json
{"type": "lobster-press/ready", "ts": 1781195281.2}
```

Then loops on stdin, dispatching `tools/call` requests and emitting responses with the matching `requestId`. See `index.ts` for the canonical client implementation.

## Testing

```bash
pytest tests/integration/test_mcp_e2e.py -v
```

The 6 e2e tests spawn this server as a subprocess and assert the ingest → grep → status → assemble round-trip end-to-end. They are the integration gate that catches schema / namespace / seq regressions before they hit production.

## Legacy note

The v2-era tool list (`compress_session` / `preview_compression` / `get_compression_stats` / `update_weights` / `list_sessions`) is **not** part of v5.0. The 17 tools above are the authoritative current surface; any client still calling the v2 names will receive a `Unknown tool` error.
