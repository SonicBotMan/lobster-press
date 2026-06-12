#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for CHLRScorer (src/pipeline/chlr_scorer.py)."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from src.pipeline.chlr_scorer import CHLRScorer


# ---------- helpers ----------

def _msg(**kw):
    base = {"id": "m1", "token_count": 0, "metadata": {"entities": []}, "content": ""}
    base.update(kw)
    return base


def _iso(dt):
    return dt.isoformat()


# ---------- calculate_complexity (pure math) ----------

class TestCalculateComplexity:
    def test_empty_message_is_zero(self):
        assert CHLRScorer().calculate_complexity({}) == 0.0

    def test_long_token_count_saturates_token_factor(self):
        # 500 tokens -> full 0.3 token bucket
        assert CHLRScorer().calculate_complexity(
            {"token_count": 500, "content": ""}
        ) == pytest.approx(0.3, abs=1e-9)

    def test_very_long_tokens_still_capped(self):
        assert CHLRScorer().calculate_complexity(
            {"token_count": 100_000, "content": ""}
        ) == pytest.approx(0.3, abs=1e-9)

    def test_ten_entities_saturate_entity_factor(self):
        msg = {"token_count": 0, "metadata": {"entities": ["x"]*10}, "content": ""}
        assert CHLRScorer().calculate_complexity(msg) == pytest.approx(0.3, abs=1e-9)

    def test_metadata_as_json_string_parses(self):
        msg = {"token_count": 0, "metadata": '{"entities":["a","b","c"]}', "content": ""}
        assert CHLRScorer().calculate_complexity(msg) == pytest.approx(0.09, abs=1e-9)

    def test_invalid_metadata_json_falls_back(self):
        msg = {"token_count": 0, "metadata": "{not valid", "content": ""}
        assert CHLRScorer().calculate_complexity(msg) == 0.0

    def test_code_block_in_content(self):
        msg = {"token_count": 0, "content": "```python\nprint(1)\n```"}
        assert CHLRScorer().calculate_complexity(msg) == pytest.approx(0.2, abs=1e-9)

    def test_def_keyword_in_content(self):
        msg = {"token_count": 0, "content": "def foo(): return 1"}
        assert CHLRScorer().calculate_complexity(msg) == pytest.approx(0.2, abs=1e-9)

    def test_all_factors_combined_capped_at_one(self):
        msg = {
            "token_count": 1000,
            "metadata": {"entities": list(range(50))},
            "tfidf_score": 1.0,
            "content": "```python\ndef f():\n    return 1\n```",
        }
        assert CHLRScorer().calculate_complexity(msg) == pytest.approx(1.0, abs=1e-9)


# ---------- calculate_half_life (pure math) ----------

class TestCalculateHalfLife:
    def test_zero_complexity_yields_base(self):
        s = CHLRScorer(base_h=12.0, alpha=0.1)
        assert s.calculate_half_life({}) == pytest.approx(12.0, abs=1e-9)

    def test_full_complexity_scales(self):
        s = CHLRScorer(base_h=12.0, alpha=0.1)
        # complexity=1.0 -> h = 12 * 1.1 = 13.2
        msg = {
            "token_count": 1000,
            "metadata": {"entities": list(range(10))},
            "tfidf_score": 1.0,
            "content": "```def f():\n```",
        }
        assert s.calculate_half_life(msg) == pytest.approx(13.2, abs=1e-9)

    def test_partial_complexity_custom_params(self):
        # base_h=24, alpha=0.5, entities=5 -> 0.15, tokens=250 -> 0.15
        # complexity = 0.30 -> h = 24 * (1 + 0.5*0.3) = 24 * 1.15 = 27.6
        s = CHLRScorer(base_h=24.0, alpha=0.5)
        msg = _msg(
            token_count=250,
            metadata={"entities": list(range(5))},
            content="",
        )
        assert s.calculate_half_life(msg) == pytest.approx(27.6, abs=1e-9)


# ---------- calculate_retention (date-driven) ----------

class TestCalculateRetention:
    def test_no_timestamps_returns_one(self):
        assert CHLRScorer().calculate_retention({}) == pytest.approx(1.0, abs=1e-9)

    def test_just_created_returns_one(self):
        s = CHLRScorer()
        now = datetime.now(timezone.utc)
        msg = _msg(created_at=_iso(now), last_accessed_at=_iso(now))
        assert s.calculate_retention(msg, current_time=now) == pytest.approx(1.0, abs=1e-6)

    def test_one_half_life_returns_half(self):
        s = CHLRScorer(base_h=12.0)
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=12)
        msg = _msg(created_at=_iso(past), last_accessed_at=_iso(past))
        # After one half-life, retention = 2^(-12/12) = 0.5
        assert s.calculate_retention(msg, current_time=now) == pytest.approx(0.5, abs=1e-6)

    def test_two_half_lives_returns_quarter(self):
        s = CHLRScorer(base_h=10.0)
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=20)
        msg = _msg(created_at=_iso(past), last_accessed_at=_iso(past))
        # 2 half-lives -> 2^(-20/10) = 0.25
        assert s.calculate_retention(msg, current_time=now) == pytest.approx(0.25, abs=1e-6)

    def test_retention_monotonically_decreasing_with_age(self):
        s = CHLRScorer(base_h=12.0)
        now = datetime.now(timezone.utc)
        prev = 1.1
        for h in [0, 1, 5, 10, 24, 100, 1000]:
            past = now - timedelta(hours=h)
            msg = _msg(created_at=_iso(past), last_accessed_at=_iso(past))
            r = s.calculate_retention(msg, current_time=now)
            assert 0.0 <= r <= 1.0
            assert r <= prev + 1e-9
            prev = r

    def test_invalid_timestamp_returns_one(self):
        assert CHLRScorer().calculate_retention(
            {"created_at": "not a date"}
        ) == pytest.approx(1.0, abs=1e-9)

    def test_zero_half_life_returns_zero(self):
        s = CHLRScorer(base_h=0.0, alpha=0.0)
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)
        msg = _msg(created_at=_iso(past), last_accessed_at=_iso(past))
        assert s.calculate_retention(msg, current_time=now) == 0.0


# ---------- should_promote / should_decay ----------
# Mock calculate_retention to remove datetime.now(timezone.utc) dependence.

class TestPromotionAndDecay:
    def test_working_high_retention_promotes(self):
        with patch.object(CHLRScorer, "calculate_retention", return_value=0.9):
            assert CHLRScorer().should_promote(_msg(memory_tier="working")) is True

    def test_working_low_retention_does_not_promote(self):
        with patch.object(CHLRScorer, "calculate_retention", return_value=0.3):
            assert CHLRScorer().should_promote(_msg(memory_tier="working")) is False

    def test_episodic_needs_retention_and_access(self):
        with patch.object(CHLRScorer, "calculate_retention", return_value=0.9):
            assert CHLRScorer().should_promote(
                _msg(memory_tier="episodic", access_count=3)
            ) is True
            assert CHLRScorer().should_promote(
                _msg(memory_tier="episodic", access_count=2)
            ) is False
            with patch.object(CHLRScorer, "calculate_retention", return_value=0.5):
                assert CHLRScorer().should_promote(
                    _msg(memory_tier="episodic", access_count=10)
                ) is False

    def test_semantic_never_promotes(self):
        with patch.object(CHLRScorer, "calculate_retention", return_value=1.0):
            assert CHLRScorer().should_promote(
                _msg(memory_tier="semantic", access_count=100)
            ) is False

    def test_decay_below_default_threshold(self):
        with patch.object(CHLRScorer, "calculate_retention", return_value=0.2):
            assert CHLRScorer().should_decay(_msg()) is True

    def test_decay_above_default_threshold(self):
        with patch.object(CHLRScorer, "calculate_retention", return_value=0.5):
            assert CHLRScorer().should_decay(_msg()) is False

    def test_decay_custom_threshold(self):
        with patch.object(CHLRScorer, "calculate_retention", return_value=0.5):
            assert CHLRScorer().should_decay(_msg(), threshold=0.6) is True


# ---------- batch_calculate ----------

class TestBatchCalculate:
    def test_empty_list_returns_empty(self):
        assert CHLRScorer().batch_calculate([]) == []

    def test_batch_enriches_each_message(self):
        s = CHLRScorer(base_h=12.0)
        now = datetime.now(timezone.utc)
        # 'rich' has 0.3 (token) + 0.3 (entities) = 0.6 complexity
        # 'plain' has 0.0 complexity
        rich = _msg(
            id="rich", token_count=500,
            metadata={"entities": ["e"]*10}, content="x",
            created_at=_iso(now), last_accessed_at=_iso(now),
        )
        plain = _msg(
            id="plain", token_count=0, content="x",
            created_at=_iso(now), last_accessed_at=_iso(now),
        )
        out = s.batch_calculate([rich, plain])
        assert len(out) == 2
        for m in out:
            assert "half_life" in m
            assert "retention" in m
            assert m["half_life"] > 0
            assert 0.0 <= m["retention"] <= 1.0
        # rich half_life = 12 * (1 + 0.1*0.6) = 12.72
        # plain half_life = 12 * 1.0 = 12.0
        assert out[0]["half_life"] > out[1]["half_life"]

    def test_batch_preserves_input_order(self):
        s = CHLRScorer()
        msgs = [_msg(id=f"m{i}") for i in range(3)]
        out = s.batch_calculate(msgs)
        assert [m["id"] for m in out] == ["m0", "m1", "m2"]

    def test_batch_does_not_mutate_input(self):
        s = CHLRScorer()
        m = _msg(token_count=100, metadata={"entities": ["a"]})
        original = m.copy()
        s.batch_calculate([m])
        assert m == original
