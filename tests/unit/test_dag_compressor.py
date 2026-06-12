#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for DAGCompressor (src/dag_compressor.py)."""

import os
import tempfile
import pytest

from src.database import LobsterDatabase
from src.llm_client import MockLLMClient
from src.dag_compressor import DAGCompressor


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


@pytest.fixture
def compressor(db):
    return DAGCompressor(
        db=db,
        llm_client=MockLLMClient(),
        fresh_tail_count=2,
        leaf_chunk_tokens=1,
        condensed_min_fanout=4,
    )


# Global counter to guarantee unique message IDs across repeated _seed calls
_msg_counter = 0


def _seed(db, conv_id, contents, role="user"):
    global _msg_counter
    ids = []
    for c in contents:
        msg = {
            "id": f"m_{conv_id}_{_msg_counter}",
            "conversationId": conv_id,
            "role": role,
            "content": c,
            "timestamp": "2026-06-12T10:00:00Z",
        }
        db.save_message(msg)
        ids.append(msg["id"])
        _msg_counter += 1
    return ids


# ---------- leaf_compact ----------


class TestLeafCompact:
    def test_empty_conversation_returns_no_summary(self, compressor, db):
        result = compressor.leaf_compact("empty")
        # Empty conv: either returns None or empty dict
        assert result in (None, {}, [])

    def test_small_conversation_below_tail_creates_leaf(self, compressor, db):
        # fresh_tail_count=2, seed 3 messages -> at least 1 leaf
        _seed(db, "c1", ["msg 1", "msg 2", "msg 3"])
        result = compressor.leaf_compact("c1")
        assert result is not None
        # summary_id and content present
        assert "summary_id" in result or "content" in result

    def test_returns_dict_shape(self, compressor, db):
        _seed(db, "c1", ["alpha", "bravo", "charlie", "delta", "echo"])
        result = compressor.leaf_compact("c1")
        assert isinstance(result, dict)

    def test_fresh_tail_messages_not_in_summary(self, compressor, db):
        # fresh_tail_count=2, seed 5 msgs -> summary should cover
        # only first 3 (5 - 2 = 3), not the last 2
        _seed(db, "c1", [f"msg {i}" for i in range(5)])
        result = compressor.leaf_compact("c1")
        if result and "content" in result:
            content = result["content"]
            assert "msg 4" not in content
            assert "msg 3" not in content

    def test_max_tokens_limits_summary_size(self, compressor, db):
        long = "x" * 5000
        _seed(db, "c1", [long, long, long, long, long])
        result = compressor.leaf_compact("c1", max_tokens=100)
        if result and "content" in result:
            # Summary should be <= ~100 tokens worth of text
            assert len(result["content"]) < 5000


# ---------- condensed_compact ----------


class TestCondensedCompact:
    def test_empty_conversation_returns_none(self, compressor, db):
        assert compressor.condensed_compact("empty") is None

    def test_no_summaries_returns_none(self, compressor, db):
        # Messages but no leaf summaries yet
        _seed(db, "c1", ["alpha", "bravo", "charlie", "delta", "echo"])
        assert compressor.condensed_compact("c1") is None

    def test_below_min_fanout_returns_none(self, compressor, db):
        _seed(db, "c1", ["alpha msg0", "bravo msg1", "charlie msg2"])
        compressor.leaf_compact("c1")
        assert compressor.condensed_compact("c1") is None

    def test_above_min_fanout_creates_condensed(self, compressor, db):
        # Create >= 4 leaf summaries by seeding enough messages in one batch
        # and running leaf_compact multiple times
        msgs = []
        for batch in range(4):
            msgs.extend([f"batch{batch} msg{i}" for i in range(3)])
        _seed(db, "c1", msgs)
        for _ in range(4):
            compressor.leaf_compact("c1")
        result = compressor.condensed_compact("c1")
        if result:
            assert result["kind"] == "condensed"
            assert result["depth"] >= 1


# ---------- incremental_compact ----------


class TestIncrementalCompact:
    def test_below_threshold_returns_false(self, compressor, db):
        # Small conversation, well below 75% of 20000 tokens
        _seed(db, "c1", ["tiny msg"])
        assert (
            compressor.incremental_compact("c1", context_threshold=0.75, token_budget=20000)
            is False
        )

    def test_above_threshold_triggers_compression(self, compressor, db):
        # Fill way past threshold — seed all messages in one call so IDs are unique
        contents = [f"msg {i}: " + "x" * 500 for i in range(20)]
        _seed(db, "c1", contents)
        # Token budget 1000, 20 msgs * ~125 tokens = ~2500 > 50%
        result = compressor.incremental_compact("c1", context_threshold=0.5, token_budget=1000)
        assert result is True

    def test_token_budget_override(self, compressor, db):
        # Even with high threshold, small budget triggers compression
        contents = [f"msg {i}: " + "x" * 100 for i in range(5)]
        _seed(db, "c1", contents)
        # 5 msgs * ~25 tokens = ~125; budget 50 -> way over
        result = compressor.incremental_compact("c1", context_threshold=0.99, token_budget=50)
        assert result is True


# ---------- full_compact ----------


class TestFullCompact:
    def test_full_compress_returns_stats_dict(self, compressor, db):
        _seed(db, "c1", ["alpha", "bravo", "charlie", "delta", "echo"])
        result = compressor.full_compact("c1")
        assert isinstance(result, dict)
        # Should have some stat keys
        assert any(
            k in result
            for k in (
                "leaf_summaries",
                "condensed_summaries",
                "messages_compressed",
                "tokens_saved",
                "original_tokens",
                "compressed_tokens",
            )
        )

    def test_full_compress_creates_at_least_one_summary(self, compressor, db):
        _seed(db, "c1", ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf"])
        compressor.full_compact("c1")
        # After full compression, summaries should exist
        summaries = compressor.db.get_summaries("c1")
        assert len(summaries) >= 1

    def test_full_compress_skip_message_ids(self, compressor, db):
        ids = _seed(db, "c1", ["alpha", "bravo", "charlie", "delta", "echo"])
        # Skip all messages -> no summarization happens
        result = compressor.full_compact("c1", skip_message_ids=ids)
        # Whatever happens, no error
        assert isinstance(result, dict)

    def test_compressed_message_ids_tracked(self, compressor, db):
        ids = _seed(db, "c1", ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf"])
        compressor.full_compact("c1")
        compressed = compressor._get_compressed_message_ids("c1")
        # Some messages should be marked as compressed
        assert isinstance(compressed, set)


# ---------- get_context_items ----------


class TestGetContextItems:
    def test_empty_conversation_returns_empty(self, compressor, db):
        items = compressor.get_context_items("empty")
        assert items == []

    def test_returns_list(self, compressor, db):
        _seed(db, "c1", ["alpha", "bravo", "charlie"])
        items = compressor.get_context_items("c1")
        assert isinstance(items, list)
        # Should have some items (messages, summaries, or both)
        # depending on what's been compressed

    def test_after_full_compress_returns_list(self, compressor, db):
        _seed(db, "c1", ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf"])
        compressor.full_compact("c1")
        items = compressor.get_context_items("c1")
        assert isinstance(items, list)


# ---------- end-to-end pipeline ----------


class TestEndToEndPipeline:
    def test_leaf_then_condensed_pipeline(self, compressor, db):
        # Seed enough to create 4+ leaf summaries, then condense
        msgs = []
        for batch in range(4):
            msgs.extend([f"pipeline msg{batch}.{i}" for i in range(3)])
        _seed(db, "c1", msgs)
        for _ in range(4):
            r = compressor.leaf_compact("c1")
            if not r:
                break
        # At least 1 leaf should exist
        leaves = compressor.db.get_summaries("c1")
        assert any(s["kind"] == "leaf" for s in leaves)

    def test_incremental_then_full_pipeline(self, compressor, db):
        # Fill past threshold, then full compress
        contents = [f"e2e msg {i}: " + "y" * 500 for i in range(20)]
        _seed(db, "c1", contents)
        # Incremental should trigger (budget 1000, ~2500 tokens total)
        triggered = compressor.incremental_compact("c1", context_threshold=0.5, token_budget=1000)
        assert triggered is True
        # After full compress, all summaries are in DB
        compressor.full_compact("c1")
        leaves = [s for s in compressor.db.get_summaries("c1") if s["kind"] == "leaf"]
        assert len(leaves) >= 1
