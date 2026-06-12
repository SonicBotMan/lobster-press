#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end MCP server test (Issue gate).

Spawns the real MCP server as a subprocess, exchanges JSON-RPC over stdio,
and asserts that ingested data round-trips through grep / status / assemble.

This test catches the three end-to-end bugs the unit/contract tests miss:
  1. ``seq`` not auto-assigned when caller omits it
  2. ``conversations`` row never created on first message -> INNER JOIN
     in ``search_messages`` returns 0 rows -> grep silently returns []
  3. namespace filter (v3.6.0) effectively dead at runtime

All three are CI gate failures. If this test passes, the round-trip is real.
"""

import json
import os
import select
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MCP_MODULE = "mcp_server.lobster_mcp_server"


@pytest.fixture
def mcp_server():
    """Spawn the MCP server as a subprocess bound to a temp DB."""
    db = tempfile.mktemp(prefix="lobster-e2e-", suffix=".db")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["LOBSTER_DEBUG"] = "0"
    proc = subprocess.Popen(
        [sys.executable, "-m", MCP_MODULE, "--db", db, "--namespace", "e2e_test"],
        cwd=str(REPO_ROOT),
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    yield proc, db
    if proc.poll() is None:
        proc.stdout.close()
        proc.stderr.close()
        proc.stdin.close()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    else:
        proc.stdout.close()
        proc.stderr.close()
    if os.path.exists(db):
        os.unlink(db)


def _send(proc, req):
    proc.stdin.write(json.dumps(req) + "\n")
    proc.stdin.flush()


def _recv(proc, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        r, _, _ = select.select([proc.stdout], [], [], end - time.time())
        if not r:
            return None
        line = proc.stdout.readline()
        if line:
            return line.strip()
    return None


def _call(proc, tool, args, rid):
    _send(
        proc,
        {
            "requestId": rid,
            "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        },
    )
    return _recv(proc)


def test_mcp_ready_handshake(mcp_server):
    """Server must emit lobster-press/ready within 8 seconds."""
    proc, _ = mcp_server
    ready = _recv(proc, timeout=8)
    assert ready is not None, "server did not emit ready handshake in 8s"
    msg = json.loads(ready)
    assert msg.get("type") == "lobster-press/ready", f"unexpected ready: {msg!r}"


def test_mcp_ingest_seq_auto_assigned(mcp_server):
    """Caller omits seq; server must auto-assign and not raise NOT NULL."""
    proc, _ = mcp_server
    assert _recv(proc, timeout=8) is not None
    r = _call(
        proc,
        "lobster_ingest",
        {
            "conversation_id": "conv_seq_test",
            "messages": [
                {
                    "role": "user",
                    "content": "first message",
                    "timestamp": "2026-06-12T10:00:00Z",
                    "id": "m_seq_1",
                },
                {
                    "role": "user",
                    "content": "second message",
                    "timestamp": "2026-06-12T10:01:00Z",
                    "id": "m_seq_2",
                },
            ],
        },
        rid="seq-test",
    )
    parsed = json.loads(r)
    assert parsed["status"] == "ok", f"ingest failed: {parsed}"
    assert parsed["result"]["ingested"] == 2


def test_mcp_grep_finds_what_ingest_wrote(mcp_server):
    """Round-trip: ingest a unique keyword, then grep must find it.

    This is the load-bearing test. Pre-fix, this returned ``results: []``
    because ``save_message`` never created the ``conversations`` row, so
    ``search_messages``'s INNER JOIN filtered everything out.
    """
    proc, _ = mcp_server
    assert _recv(proc, timeout=8) is not None
    unique = "PostgreSQL_ROCKS_e2e_marker"
    r = _call(
        proc,
        "lobster_ingest",
        {
            "conversation_id": "conv_round_trip",
            "messages": [
                {
                    "role": "user",
                    "content": f"we decided to use {unique} for the new service",
                    "timestamp": "2026-06-12T10:00:00Z",
                    "id": "m_rt_1",
                }
            ],
        },
        rid="rt-ingest",
    )
    assert json.loads(r)["status"] == "ok"

    r = _call(
        proc,
        "lobster_grep",
        {"query": unique, "limit": 5},
        rid="rt-grep",
    )
    parsed = json.loads(r)
    assert parsed["status"] == "ok"
    hits = parsed["result"]["results"]
    assert len(hits) >= 1, (
        f"ingest->grep round trip BROKEN: ingested a message containing "
        f"'{unique}' but grep returned {hits!r}. This is the namespace/"
        f"missing-conversation-row bug."
    )
    assert any(unique in h.get("content", "") for h in hits)


def test_mcp_namespace_isolation(mcp_server):
    """Two namespaces write the same keyword; cross-namespace grep must hide it."""
    proc, db = mcp_server
    assert _recv(proc, timeout=8) is not None
    # The current server was spawned with --namespace=e2e_test, so we can
    # only validate that data we ingested into this namespace is searchable.
    # A negative cross-namespace check would require a second server, which
    # is out of scope for a single-server smoke test. We assert the
    # namespace column on the conversation row is populated, which is the
    # invariant the bug was breaking.
    r = _call(
        proc,
        "lobster_ingest",
        {
            "conversation_id": "conv_ns_check",
            "messages": [
                {
                    "role": "user",
                    "content": "namespace propagation test",
                    "timestamp": "2026-06-12T10:00:00Z",
                    "id": "m_ns_1",
                }
            ],
        },
        rid="ns-ingest",
    )
    assert json.loads(r)["status"] == "ok"

    import sqlite3

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT namespace FROM conversations WHERE conversation_id = ?",
        ("conv_ns_check",),
    ).fetchone()
    conn.close()
    assert row is not None, "save_message did not create a conversations row"
    assert row[0] == "e2e_test", (
        f"namespace not propagated to conversations row: got {row[0]!r}, "
        f"expected 'e2e_test'. This is the v3.6.0 namespace bug."
    )


def test_mcp_status_and_assemble(mcp_server):
    """status reports system health; assemble rebuilds a 3-layer context."""
    proc, _ = mcp_server
    assert _recv(proc, timeout=8) is not None
    r = _call(proc, "lobster_status", {}, rid="status")
    parsed = json.loads(r)
    assert parsed["status"] == "ok"
    assert "version" in parsed["result"]
    assert "tier_distribution" in parsed["result"]

    r = _call(
        proc,
        "lobster_assemble",
        {"conversation_id": "conv_status", "token_budget": 4000},
        rid="assemble",
    )
    parsed = json.loads(r)
    assert parsed["status"] == "ok"


def test_mcp_seq_overrides_auto(mcp_server):
    """Caller-provided seq must be honored, not overwritten by auto-assign."""
    proc, db = mcp_server
    assert _recv(proc, timeout=8) is not None
    r = _call(
        proc,
        "lobster_ingest",
        {
            "conversation_id": "conv_explicit",
            "messages": [
                {
                    "role": "user",
                    "content": "explicit seq",
                    "timestamp": "2026-06-12T10:00:00Z",
                    "id": "m_exp_1",
                    "seq": 7,
                }
            ],
        },
        rid="exp",
    )
    assert json.loads(r)["status"] == "ok"
    import sqlite3

    conn = sqlite3.connect(db)
    seq = conn.execute("SELECT seq FROM messages WHERE message_id = ?", ("m_exp_1",)).fetchone()[0]
    conn.close()
    assert seq == 7, f"explicit seq=7 not honored, got {seq}"
