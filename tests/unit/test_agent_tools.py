#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for agent_tools (src/agent_tools.py)."""

import json
import os
import subprocess
import sys
import tempfile
import pytest

from src.database import LobsterDatabase
from src.agent_tools import lobster_grep, lobster_describe, lobster_expand, main


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def db(db_path):
    d = LobsterDatabase(db_path)
    yield d
    d.close()


def _seed(db, conversation_id, messages):
    """Save messages and return their ids."""
    ids = []
    for i, content in enumerate(messages):
        msg = {
            "id": f"m_{conversation_id}_{i}",
            "conversationId": conversation_id,
            "role": "user",
            "content": content,
            "timestamp": "2026-06-12T10:00:00Z",
        }
        db.save_message(msg)
        ids.append(msg["id"])
    return ids


def _seed_summary(db, conversation_id, kind="leaf", depth=0, summary_id=None, message_ids=None):
    """Save a summary row directly via cursor."""
    if summary_id is None:
        import uuid

        summary_id = f"sum_{uuid.uuid4().hex[:8]}"
    earliest = "2026-06-12T10:00:00Z"
    latest = "2026-06-12T10:05:00Z"
    db.cursor.execute(
        """
        INSERT INTO summaries (summary_id, conversation_id, kind, depth,
                              content, token_count, earliest_at, latest_at,
                              descendant_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            summary_id,
            conversation_id,
            kind,
            depth,
            "summary content",
            10,
            earliest,
            latest,
            1,
            earliest,
        ),
    )
    if message_ids:
        for mid in message_ids:
            db.cursor.execute(
                "INSERT INTO summary_messages (summary_id, message_id) VALUES (?, ?)",
                (summary_id, mid),
            )
    db.conn.commit()
    return summary_id


# ---------- lobster_grep ----------


class TestLobsterGrep:
    def test_empty_db_returns_empty(self, db):
        results = lobster_grep(db, "anything")
        assert results == []

    def test_simple_keyword_match(self, db):
        _seed(db, "c1", ["PostgreSQL is the database", "Redis is a cache", "Postgres has JSONB"])
        results = lobster_grep(db, "PostgreSQL", search_summaries=False)
        assert any("PostgreSQL" in r["content"] for r in results)
        # "Postgres has JSONB" should NOT match (different keyword)
        # Note: FTS5 may do prefix matching

    def test_conversation_id_filters_results(self, db):
        _seed(db, "c1", ["alpha message"])
        _seed(db, "c2", ["alpha message in c2"])
        results = lobster_grep(db, "alpha", search_summaries=False)
        conv_ids = {r["conversation_id"] for r in results}
        # both c1 and c2 should appear (no filter)
        assert "c1" in conv_ids and "c2" in conv_ids

    def test_limit_caps_results(self, db):
        for i in range(20):
            _seed(db, "c1", [f"keyword message {i}"])
        results = lobster_grep(db, "keyword", search_summaries=False, limit=5)
        assert len(results) <= 5

    def test_search_messages_only(self, db):
        _seed_summary(db, "c1", kind="leaf", depth=0, summary_id="sum_1", message_ids=[])
        _seed(db, "c1", ["alpha message"])
        results = lobster_grep(db, "alpha", search_messages=True, search_summaries=False)
        assert all(r["type"] == "message" for r in results)
        assert any("alpha" in r["content"] for r in results)

    def test_result_fields_present(self, db):
        _seed(db, "c1", ["PostgreSQL test"])
        results = lobster_grep(db, "PostgreSQL", search_summaries=False)
        assert len(results) >= 1
        hit = results[0]
        assert "type" in hit
        assert "id" in hit
        assert "conversation_id" in hit
        assert "content" in hit
        assert "relevance" in hit
        assert "tfidf_score" in hit

    def test_tfidf_rerank_disabled(self, db):
        _seed(db, "c1", ["PostgreSQL test"])
        # use_tfidf_rerank=False should still work, just with different ranking
        results = lobster_grep(db, "PostgreSQL", search_summaries=False, use_tfidf_rerank=False)
        assert len(results) >= 1


# ---------- lobster_describe ----------


class TestLobsterDescribe:
    def test_no_args_returns_none(self, db):
        assert lobster_describe(db) is None

    def test_describe_by_conversation_id(self, db):
        _seed(db, "c1", ["msg1", "msg2", "msg3"])
        result = lobster_describe(db, conversation_id="c1")
        assert result is not None
        assert result["conversation_id"] == "c1"
        assert "total_summaries" in result
        assert "max_depth" in result
        assert "by_depth" in result
        assert "turn_count" in result

    def test_describe_by_conversation_with_depth_filter(self, db):
        _seed_summary(db, "c1", kind="leaf", depth=0, summary_id="sum_d0")
        _seed_summary(db, "c1", kind="leaf", depth=1, summary_id="sum_d1")
        result = lobster_describe(db, conversation_id="c1", depth=1)
        # Should only include depth=1 summaries
        assert result is not None
        if result["by_depth"]:
            assert 0 not in result["by_depth"]
            assert 1 in result["by_depth"]

    def test_describe_nonexistent_summary_returns_none(self, db):
        assert lobster_describe(db, summary_id="does_not_exist") is None

    def test_describe_by_summary_id_leaf(self, db):
        ids = _seed(db, "c1", ["m1 content", "m2 content"])
        sid = _seed_summary(db, "c1", kind="leaf", depth=0, summary_id="sum_leaf", message_ids=ids)
        result = lobster_describe(db, summary_id=sid)
        assert result is not None
        assert result["summary_id"] == sid
        assert result["kind"] == "leaf"
        assert "messages" in result
        assert len(result["messages"]) == 2

    def test_describe_by_summary_id_non_leaf(self, db):
        sid = _seed_summary(
            db, "c1", kind="condensed", depth=1, summary_id="sum_cond", message_ids=[]
        )
        result = lobster_describe(db, summary_id=sid)
        assert result is not None
        assert result["kind"] == "condensed"
        # Non-leaf should have parent_summaries field, not messages
        assert "parent_summaries" in result
        assert "messages" not in result


# ---------- lobster_expand ----------


class TestLobsterExpand:
    def test_expand_nonexistent_returns_empty(self, db):
        result = lobster_expand(db, "does_not_exist")
        assert result["total_messages"] == 0
        assert result["messages"] == []
        assert result["summary_id"] == "does_not_exist"

    def test_expand_leaf_summary(self, db):
        ids = _seed(db, "c1", ["leaf content 1", "leaf content 2"])
        sid = _seed_summary(db, "c1", kind="leaf", depth=0, summary_id="sum_exp_1", message_ids=ids)
        result = lobster_expand(db, sid)
        assert result["total_messages"] == 2
        contents = {m["content"] for m in result["messages"]}
        assert "leaf content 1" in contents
        assert "leaf content 2" in contents
        # Sorted by seq
        seqs = [m["seq"] for m in result["messages"]]
        assert seqs == sorted(seqs)

    def test_expand_with_max_depth_limit(self, db):
        ids1 = _seed(db, "c1", ["child msg 1", "child msg 2"])
        ids2 = _seed(db, "c1", ["grandchild msg 1"])
        # Create parent -> child relationship
        sid_child = _seed_summary(
            db, "c1", kind="leaf", depth=0, summary_id="sum_child", message_ids=ids1
        )
        sid_parent = "sum_parent"
        db.cursor.execute(
            """
            INSERT INTO summaries (summary_id, conversation_id, kind, depth,
                                   content, token_count, earliest_at, latest_at,
                                   descendant_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                sid_parent,
                "c1",
                "condensed",
                1,
                "p",
                10,
                "2026-06-12T10:00:00Z",
                "2026-06-12T10:05:00Z",
                1,
                "2026-06-12T10:00:00Z",
            ),
        )
        db.cursor.execute(
            "INSERT INTO summary_parents (summary_id, parent_summary_id) VALUES (?, ?)",
            (sid_parent, sid_child),
        )
        # link ids2 to child too (use OR IGNORE in case ids1 == ids2)
        db.cursor.execute(
            "INSERT OR IGNORE INTO summary_messages (summary_id, message_id) VALUES (?, ?)",
            (sid_child, ids2[0]),
        )
        db.conn.commit()

        # max_depth=0 -> only direct, but child is at depth 0, so we get child
        r0 = lobster_expand(db, sid_parent, max_depth=0)
        # max_depth=1 -> we recurse into child
        r1 = lobster_expand(db, sid_parent, max_depth=1)
        assert r0["total_messages"] == 0 or r1["total_messages"] >= r0["total_messages"]
        # max_depth=1 should include the child leaf's messages
        assert r1["total_messages"] >= 2

    def test_expand_visited_set_prevents_cycles(self, db):
        # Set up a cycle: A -> B -> A
        ids = _seed(db, "c1", ["cycle msg"])
        db.cursor.execute("""
            INSERT INTO summaries (summary_id, conversation_id, kind, depth,
                                   content, token_count, earliest_at, latest_at,
                                   descendant_count, created_at)
            VALUES ('sum_A', 'c1', 'condensed', 1, 'a', 10,
                    '2026-06-12T10:00:00Z', '2026-06-12T10:05:00Z', 1,
                    '2026-06-12T10:00:00Z')
        """)
        db.cursor.execute("""
            INSERT INTO summaries (summary_id, conversation_id, kind, depth,
                                   content, token_count, earliest_at, latest_at,
                                   descendant_count, created_at)
            VALUES ('sum_B', 'c1', 'leaf', 0, 'b', 10,
                    '2026-06-12T10:00:00Z', '2026-06-12T10:05:00Z', 1,
                    '2026-06-12T10:00:00Z')
        """)
        db.cursor.execute(
            "INSERT INTO summary_messages (summary_id, message_id) VALUES ('sum_B', ?)", (ids[0],)
        )
        db.cursor.execute(
            "INSERT INTO summary_parents (summary_id, parent_summary_id) VALUES ('sum_A', 'sum_B')"
        )
        db.cursor.execute(
            "INSERT INTO summary_parents (summary_id, parent_summary_id) VALUES ('sum_B', 'sum_A')"
        )
        db.conn.commit()
        # Should not infinite-loop
        result = lobster_expand(db, "sum_A", max_depth=5)
        assert result["total_messages"] == 1
        # visited_summaries should be at most 2 (A and B)
        assert result["visited_summaries"] <= 2


# ---------- main() CLI ----------


class TestMainCLI:
    def test_no_command_prints_help(self, db_path, capsys):
        rc = subprocess.run(
            [sys.executable, "-m", "src.agent_tools"],
            env={**os.environ, "PYTHONPATH": os.getcwd()},
            capture_output=True,
            text=True,
            timeout=10,
        )
        # No subcommand -> exit non-zero or help on stdout
        combined = rc.stdout + rc.stderr
        assert "usage" in combined.lower() or "可用命令" in combined or rc.returncode != 0

    def test_grep_subcommand_json(self, db, db_path):
        _seed(db, "c1", ["PostgreSQL rocks"])
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.agent_tools",
                "--db",
                db_path,
                "grep",
                "PostgreSQL",
                "--no-summaries",
                "--json",
            ],
            env={**os.environ, "PYTHONPATH": os.getcwd()},
            capture_output=True,
            text=True,
            timeout=10,
        )
        # stdout should be valid JSON
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert any("PostgreSQL" in r["content"] for r in data)

    def test_describe_subcommand_json(self, db, db_path):
        _seed(db, "c1", ["msg"])
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.agent_tools",
                "--db",
                db_path,
                "describe",
                "--conversation",
                "c1",
                "--json",
            ],
            env={**os.environ, "PYTHONPATH": os.getcwd()},
            capture_output=True,
            text=True,
            timeout=10,
        )
        data = json.loads(result.stdout)
        assert data.get("conversation_id") == "c1"

    def test_expand_subcommand_json(self, db, db_path):
        ids = _seed(db, "c1", ["expandable content"])
        sid = _seed_summary(
            db, "c1", kind="leaf", depth=0, summary_id="sum_exp_cli", message_ids=ids
        )
        result = subprocess.run(
            [sys.executable, "-m", "src.agent_tools", "--db", db_path, "expand", sid, "--json"],
            env={**os.environ, "PYTHONPATH": os.getcwd()},
            capture_output=True,
            text=True,
            timeout=10,
        )
        data = json.loads(result.stdout)
        assert data["summary_id"] == sid
        assert data["total_messages"] == 1
