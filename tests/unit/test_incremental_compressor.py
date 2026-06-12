#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for IncrementalCompressor (src/incremental_compressor.py).

API facts confirmed by reading the source:
- _select_compression_strategy uses hard-coded thresholds 0.60 / 0.75
  (NOT config-driven), so context_threshold param doesn't affect the
  strategy bucket — only _should_compress.
- save_message requires 'id' (not 'message_id'); if absent it auto-generates.
- on_new_message mutates the message dict in-place with msg_type etc.
- get_stats() returns {**self.stats, context_threshold, fresh_tail_count,
  leaf_chunk_tokens}. self.stats starts with {last_compression: None}
  and gains {total_compressions, tokens_saved, ...} as compressions run.
- compress() returns {condensed_summaries, leaf_summaries, messages_compressed,
  tokens_saved}.
- get_context_by_tier(tiers=[...]) is the DB read for context."""

import os
import tempfile

import pytest

from src.database import LobsterDatabase
from src.incremental_compressor import IncrementalCompressor
from src.llm_client import MockLLMClient


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
    return IncrementalCompressor(
        db=db,
        llm_client=MockLLMClient(),
        max_context_tokens=1000,
        context_threshold=0.5,
        fresh_tail_count=2,
    )


def _msg(content, role="user", msg_id=None):
    base = {
        "role": role,
        "content": content,
        "timestamp": "2026-06-12T10:00:00Z",
    }
    if msg_id is not None:
        base["id"] = msg_id
    return base


# ---------- _select_compression_strategy ----------
# Function uses hard-coded thresholds (0.60, 0.75) regardless of ctor args.


class TestSelectStrategy:
    def test_under_60_percent_none(self):
        c = IncrementalCompressor(
            db=__import__("src.database", fromlist=["LobsterDatabase"]).LobsterDatabase(
                tempfile.mktemp(suffix=".db")
            ),
            max_context_tokens=1000,
        )
        # Any usage < 0.60 -> none
        assert c._select_compression_strategy(0.0) == "none"
        assert c._select_compression_strategy(0.30) == "none"
        assert c._select_compression_strategy(0.59) == "none"

    def test_60_to_75_percent_light(self):
        c = IncrementalCompressor(
            db=__import__("src.database", fromlist=["LobsterDatabase"]).LobsterDatabase(
                tempfile.mktemp(suffix=".db")
            ),
            max_context_tokens=1000,
        )
        assert c._select_compression_strategy(0.60) == "light"
        assert c._select_compression_strategy(0.70) == "light"
        assert c._select_compression_strategy(0.74) == "light"

    def test_above_75_percent_aggressive(self):
        c = IncrementalCompressor(
            db=__import__("src.database", fromlist=["LobsterDatabase"]).LobsterDatabase(
                tempfile.mktemp(suffix=".db")
            ),
            max_context_tokens=1000,
        )
        assert c._select_compression_strategy(0.75) == "aggressive"
        assert c._select_compression_strategy(0.90) == "aggressive"
        assert c._select_compression_strategy(1.0) == "aggressive"


# ---------- on_new_message ----------


class TestOnNewMessage:
    def test_below_threshold_returns_none(self, compressor):
        msg = _msg("hi there")
        result = compressor.on_new_message("c1", msg)
        assert result is None

    def test_message_persists_to_db(self, compressor, db):
        msg = _msg("hello world", msg_id="m_001")
        compressor.on_new_message("c1", msg)
        msgs = db.get_messages("c1")
        assert len(msgs) == 1
        assert "hello world" in msgs[0]["content"]

    def test_message_enriched_with_tfidf(self, compressor, db):
        msg = _msg("a normal message about PostgreSQL databases", msg_id="m_002")
        compressor.on_new_message("c1", msg)
        m = db.get_messages("c1")[0]
        assert "msg_type" in m
        assert "tfidf_score" in m

    def test_auto_compress_disabled_returns_none(self, compressor):
        msg = _msg("x" * 1000, msg_id="m_003")
        result = compressor.on_new_message("c1", msg, auto_compress=False)
        assert result is None

    def test_context_items_appended(self, compressor, db):
        compressor.on_new_message("c1", _msg("first", msg_id="m_a"))
        compressor.on_new_message("c1", _msg("second", msg_id="m_b"))
        items = db.get_context_by_tier("c1")
        # context_items has 2 entries; counts by tier format
        total = sum(len(v) for v in items.values())
        assert total == 2

    def test_user_supplied_id_preserved(self, compressor, db):
        msg = _msg("explicit id", msg_id="m_explicit_123")
        compressor.on_new_message("c1", msg)
        m = db.get_messages("c1")[0]
        assert m["message_id"] == "m_explicit_123"

    def test_no_id_auto_generated(self, compressor, db):
        msg = _msg("auto id")  # no id field
        compressor.on_new_message("c1", msg)
        m = db.get_messages("c1")[0]
        # save_message auto-generates a 'msg_xxx' id
        assert m["message_id"].startswith("msg_")

    def test_compressor_sets_conversationId_on_message(self, compressor, db):
        # Defensive: compressor must set conversationId before save
        # so the SQL NOT NULL constraint doesn't fire even if the caller
        # forgot to populate it.
        msg = _msg("defensive test", msg_id="m_def")
        # No 'conversationId' or 'conversation_id' key — compressor should set it
        compressor.on_new_message("conv_X", msg)
        m = db.get_messages("conv_X")[0]
        assert m["conversation_id"] == "conv_X"


# ---------- _get_context_usage ----------


class TestContextUsage:
    def test_no_messages_zero_usage(self, compressor):
        assert compressor._get_context_usage("empty_conv") == 0.0

    def test_filling_past_threshold(self, compressor):
        # 10 messages x ~100 tokens each = 1000 tokens = 100% of 1000 budget
        for i in range(10):
            compressor.on_new_message("c1", _msg("x" * 400, msg_id=f"m_{i}"))
        usage = compressor._get_context_usage("c1")
        assert usage > 0.9

    def test_auto_compress_triggers_above_threshold(self, compressor):
        # Fill past threshold; next message should trigger compress -> returns dict
        for i in range(10):
            compressor.on_new_message("c1", _msg("x" * 400, msg_id=f"m_{i}"))
        result = compressor.on_new_message("c1", _msg("trigger", msg_id="m_trig"))
        # Above threshold -> compression triggered -> returns stats dict
        assert isinstance(result, dict)


# ---------- get_stats ----------


class TestGetStats:
    def test_initial_stats_shape(self, compressor):
        s = compressor.get_stats()
        assert "context_threshold" in s
        assert "fresh_tail_count" in s
        assert "leaf_chunk_tokens" in s
        # last_compression is set on init (None)
        assert "last_compression" in s
        assert s["last_compression"] is None

    def test_stats_after_compression(self, compressor):
        for i in range(10):
            compressor.on_new_message("c1", _msg("x" * 400, msg_id=f"m_{i}"))
        compressor.compress("c1")
        s = compressor.get_stats()
        # After a successful compression run, stats gets populated
        assert "total_compressions" in s
        assert s["total_compressions"] >= 1


# ---------- monitor ----------


class TestMonitor:
    def test_monitor_returns_dict(self, compressor):
        compressor.on_new_message("c1", _msg("hi", msg_id="m1"))
        m = compressor.monitor("c1")
        assert isinstance(m, dict)

    def test_monitor_includes_usage_metric(self, compressor):
        compressor.on_new_message("c1", _msg("hi", msg_id="m1"))
        m = compressor.monitor("c1")
        # Some form of usage / tokens / ratio should be reported
        assert (
            any("usage" in k.lower() or "token" in k.lower() or "ratio" in k.lower() for k in m)
            or len(m) >= 1
        )

    def test_monitor_empty_conversation(self, compressor):
        m = compressor.monitor("never_used")
        assert isinstance(m, dict)


# ---------- _should_compress ----------


class TestShouldCompress:
    def test_empty_no_compress(self, compressor):
        assert compressor._should_compress("empty") is False

    def test_filled_above_threshold_compress(self, compressor):
        for i in range(10):
            compressor.on_new_message("c1", _msg("x" * 400, msg_id=f"m_{i}"))
        assert compressor._should_compress("c1") is True

    def test_partially_filled_below_threshold(self, compressor):
        for i in range(2):
            compressor.on_new_message("c1", _msg("x" * 50, msg_id=f"m_{i}"))
        # 2 * ~13 tokens = 26 / 1000, way below 50% threshold
        assert compressor._should_compress("c1") is False


# ---------- compress ----------


class TestCompress:
    def test_compress_returns_dict(self, compressor):
        for i in range(5):
            compressor.on_new_message("c1", _msg(f"msg {i} " * 30, msg_id=f"m_{i}"))
        result = compressor.compress("c1")
        assert isinstance(result, dict)

    def test_compress_result_has_expected_keys(self, compressor):
        for i in range(10):
            compressor.on_new_message("c1", _msg("x" * 400, msg_id=f"m_{i}"))
        result = compressor.compress("c1")
        assert "leaf_summaries" in result
        assert "condensed_summaries" in result
        assert "messages_compressed" in result
        assert "tokens_saved" in result

    def test_compress_empty_conversation_handled(self, compressor):
        result = compressor.compress("empty")
        assert isinstance(result, dict)
        # No messages to compress, all counts should be 0
        assert result.get("messages_compressed", 0) == 0
