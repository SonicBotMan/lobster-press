"""Unit tests for HybridRetriever - FTS5 + Vector → RRF → MMR → Time Decay pipeline."""

import math
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


from src.vector.retriever import HybridRetriever


class TestRRFFusion:
    """Tests for _rrf_fuse method."""

    def test_two_lists_merge_correctly(self):
        """Two result lists should merge into fused dict."""
        retriever = HybridRetriever(db=MagicMock())
        list_a = [
            {
                "target_id": "A",
                "target_type": "message",
                "content": "x",
                "created_at": "",
            },
        ]
        list_b = [
            {
                "target_id": "B",
                "target_type": "summary",
                "content": "y",
                "created_at": "",
            },
        ]
        fused = retriever._rrf_fuse([list_a, list_b])
        assert "A" in fused
        assert "B" in fused
        assert len(fused) == 2

    def test_same_item_accumulates_scores(self):
        """Same item in multiple lists should accumulate RRF scores."""
        retriever = HybridRetriever(db=MagicMock())
        list_a = [
            {
                "target_id": "X",
                "target_type": "message",
                "content": "",
                "created_at": "",
            },
        ]
        list_b = [
            {
                "target_id": "X",
                "target_type": "message",
                "content": "",
                "created_at": "",
            },
        ]
        fused = retriever._rrf_fuse([list_a, list_b])
        # rank 0 in both: 1/(60+0+1) + 1/(60+0+1) = 2/61
        expected = 2.0 / 61.0
        assert abs(fused["X"]["score"] - expected) < 1e-10

    def test_k60_formula_per_source(self):
        """RRF formula: 1/(k + rank + 1) for each source."""
        retriever = HybridRetriever(db=MagicMock())
        items = [
            {
                "target_id": f"id_{i}",
                "target_type": "msg",
                "content": "",
                "created_at": "",
            }
            for i in range(5)
        ]
        fused = retriever._rrf_fuse([items], k=60)
        for rank in range(5):
            tid = f"id_{rank}"
            expected = 1.0 / (60 + rank + 1)
            assert abs(fused[tid]["score"] - expected) < 1e-10

    def test_item_not_in_list_gets_zero(self):
        """Item only in one list gets 0 contribution from other lists."""
        retriever = HybridRetriever(db=MagicMock())
        list_a = [
            {
                "target_id": "only_a",
                "target_type": "message",
                "content": "",
                "created_at": "",
            },
        ]
        list_b = [
            {
                "target_id": "only_b",
                "target_type": "summary",
                "content": "",
                "created_at": "",
            },
        ]
        fused = retriever._rrf_fuse([list_a, list_b])
        # only_a is rank 0 in list_a, absent from list_b: score = 1/61
        assert abs(fused["only_a"]["score"] - 1.0 / 61.0) < 1e-10
        assert abs(fused["only_b"]["score"] - 1.0 / 61.0) < 1e-10

    def test_empty_input_lists(self):
        """Empty result lists should produce empty fused dict."""
        retriever = HybridRetriever(db=MagicMock())
        fused = retriever._rrf_fuse([[], []])
        assert fused == {}

    def test_preserves_metadata(self):
        """RRF should preserve target_type and content from first occurrence."""
        retriever = HybridRetriever(db=MagicMock())
        items = [
            {
                "target_id": "A",
                "target_type": "message",
                "content": "hello",
                "created_at": "2024-01-01",
            },
        ]
        fused = retriever._rrf_fuse([items])
        assert fused["A"]["target_type"] == "message"
        assert fused["A"]["content"] == "hello"
        assert fused["A"]["created_at"] == "2024-01-01"


class TestMMRReranking:
    """Tests for _mmr_rerank method."""

    def test_first_item_always_selected(self):
        """First item (highest score) should always be selected first."""
        retriever = HybridRetriever(db=MagicMock())
        candidates = {
            "A": {
                "target_id": "A",
                "target_type": "msg",
                "content": "alpha",
                "score": 0.9,
            },
            "B": {
                "target_id": "B",
                "target_type": "msg",
                "content": "beta",
                "score": 0.5,
            },
        }
        results = retriever._mmr_rerank(candidates, top_k=2)
        assert results[0]["target_id"] == "A"

    def test_returns_exactly_top_k(self):
        """Should return exactly top_k items."""
        retriever = HybridRetriever(db=MagicMock())
        candidates = {
            f"id_{i}": {
                "target_id": f"id_{i}",
                "target_type": "msg",
                "content": f"content {i}",
                "score": 1.0 / (i + 1),
            }
            for i in range(10)
        }
        results = retriever._mmr_rerank(candidates, top_k=4)
        assert len(results) == 4

    def test_diversity_penalty_for_similar_items(self):
        """Similar items should be penalized via diversity."""
        retriever = HybridRetriever(db=MagicMock())
        same_content = "identical text for testing"
        candidates = {
            "A": {
                "target_id": "A",
                "target_type": "msg",
                "content": same_content,
                "score": 1.0,
            },
            "B": {
                "target_id": "B",
                "target_type": "msg",
                "content": same_content,
                "score": 0.5,
            },
            "C": {
                "target_id": "C",
                "target_type": "msg",
                "content": "zzzzzzzzzzzzzzzzzzz",
                "score": 0.45,
            },
        }
        results = retriever._mmr_rerank(candidates, top_k=3)
        ids = [r["target_id"] for r in results]
        # MMR(B) = 0.7*0.5 - 0.3*1.0 = 0.05, MMR(C) ≈ 0.7*0.45 - 0.3*~0 = 0.315
        assert ids.index("C") < ids.index("B")

    def test_lambda_bias_toward_relevance(self):
        """λ=0.7 means relevance weight is 0.7, diversity weight is 0.3."""
        retriever = HybridRetriever(db=MagicMock())
        candidates = {
            "high_rel_similar": {
                "target_id": "high_rel_similar",
                "target_type": "msg",
                "content": "aaa",
                "score": 1.0,
            },
            "low_rel_diff": {
                "target_id": "low_rel_diff",
                "target_type": "msg",
                "content": "zzz",
                "score": 0.3,
            },
            "mid_rel_similar": {
                "target_id": "mid_rel_similar",
                "target_type": "msg",
                "content": "aaa",
                "score": 0.8,
            },
        }
        results = retriever._mmr_rerank(candidates, top_k=3)
        # With λ=0.7, high relevance still dominates even with similarity penalty
        assert results[0]["target_id"] == "high_rel_similar"

    def test_empty_candidates_returns_empty(self):
        """Empty candidates should return empty list."""
        retriever = HybridRetriever(db=MagicMock())
        results = retriever._mmr_rerank({}, top_k=5)
        assert results == []

    def test_top_k_greater_than_candidates(self):
        """Should return all candidates when top_k exceeds available."""
        retriever = HybridRetriever(db=MagicMock())
        candidates = {
            "A": {"target_id": "A", "target_type": "msg", "content": "a", "score": 0.9},
            "B": {"target_id": "B", "target_type": "msg", "content": "b", "score": 0.5},
        }
        results = retriever._mmr_rerank(candidates, top_k=10)
        assert len(results) == 2


class TestTimeDecay:
    """Tests for _apply_retrieval_decay method."""

    def test_recent_items_little_decay(self):
        """Recent items should retain most of their score."""
        retriever = HybridRetriever(db=MagicMock())
        now = datetime.utcnow().isoformat()
        results = [{"score": 1.0, "created_at": now}]
        decayed = retriever._apply_retrieval_decay(results)
        # t=0: decay = 0.3 + 0.7 * 0.5^0 = 0.3 + 0.7 = 1.0
        assert abs(decayed[0]["score"] - 1.0) < 1e-6

    def test_14day_old_half_decay(self):
        """14-day old items: score × (0.3 + 0.7 × 0.5) = score × 0.65."""
        retriever = HybridRetriever(db=MagicMock())
        created = (datetime.utcnow() - timedelta(days=14)).isoformat()
        results = [{"score": 1.0, "created_at": created}]
        decayed = retriever._apply_retrieval_decay(results)
        expected = 0.3 + 0.7 * 0.5  # = 0.65
        assert abs(decayed[0]["score"] - expected) < 1e-4

    def test_very_old_items_floor_0_3(self):
        """Very old items (999d) should approach floor of score × 0.3."""
        retriever = HybridRetriever(db=MagicMock())
        created = (datetime.utcnow() - timedelta(days=999)).isoformat()
        results = [{"score": 1.0, "created_at": created}]
        decayed = retriever._apply_retrieval_decay(results)
        # decay ≈ 0.3 + 0.7 * 0.5^(999/14) ≈ 0.3 (practically)
        assert abs(decayed[0]["score"] - 0.3) < 0.01

    def test_no_timestamp_gives_floor(self):
        """Items without timestamp should get floor value (score × 0.3)."""
        retriever = HybridRetriever(db=MagicMock())
        results = [{"score": 1.0, "created_at": ""}]
        decayed = retriever._apply_retrieval_decay(results)
        assert abs(decayed[0]["score"] - 0.3) < 1e-6

    def test_invalid_timestamp_gives_floor(self):
        """Invalid timestamp strings should also get floor value."""
        retriever = HybridRetriever(db=MagicMock())
        results = [{"score": 1.0, "created_at": "not-a-date"}]
        decayed = retriever._apply_retrieval_decay(results)
        # Invalid date → t_days=999 → decay ≈ 0.3
        assert abs(decayed[0]["score"] - 0.3) < 0.01

    def test_preserves_result_count(self):
        """Decay should not change the number of results."""
        retriever = HybridRetriever(db=MagicMock())
        results = [
            {"score": 1.0, "created_at": datetime.utcnow().isoformat()},
            {"score": 0.8, "created_at": ""},
            {"score": 0.5, "created_at": "invalid"},
        ]
        decayed = retriever._apply_retrieval_decay(results)
        assert len(decayed) == 3

    def test_7day_old_partial_decay(self):
        """7-day old items should be between fresh and 14-day decay."""
        retriever = HybridRetriever(db=MagicMock())
        created = (datetime.utcnow() - timedelta(days=7)).isoformat()
        results = [{"score": 1.0, "created_at": created}]
        decayed = retriever._apply_retrieval_decay(results)
        # decay = 0.3 + 0.7 * 0.5^(7/14) = 0.3 + 0.7 * 0.7071 ≈ 0.795
        assert 0.75 < decayed[0]["score"] < 0.85


class TestTextSimilarity:
    """Tests for _text_similarity method."""

    def test_identical_strings_return_one(self):
        """Identical strings should return 1.0."""
        retriever = HybridRetriever(db=MagicMock())
        sim = retriever._text_similarity("hello world", "hello world")
        assert abs(sim - 1.0) < 1e-6

    def test_no_overlap_returns_zero(self):
        """Completely different characters should return 0.0."""
        retriever = HybridRetriever(db=MagicMock())
        sim = retriever._text_similarity("abc", "xyz")
        assert sim == 0.0

    def test_partial_overlap_between_zero_and_one(self):
        """Partial overlap should return value between 0 and 1."""
        retriever = HybridRetriever(db=MagicMock())
        sim = retriever._text_similarity("abcdef", "defghi")
        assert 0.0 < sim < 1.0

    def test_empty_string_returns_zero(self):
        """Empty strings should return 0.0."""
        retriever = HybridRetriever(db=MagicMock())
        assert retriever._text_similarity("", "hello") == 0.0
        assert retriever._text_similarity("hello", "") == 0.0
        assert retriever._text_similarity("", "") == 0.0

    def test_uses_first_200_chars(self):
        """Similarity should only consider first 200 characters."""
        retriever = HybridRetriever(db=MagicMock())
        a = "a" * 300
        b = "a" * 200 + "b" * 100
        # First 200 chars are identical: 'a'*200
        sim = retriever._text_similarity(a, b)
        assert abs(sim - 1.0) < 1e-6


class TestFTSSearch:
    """Tests for _fts_search method."""

    def _make_mock_db(self, msgs=None, sums=None):
        db = MagicMock()
        db.search_messages.return_value = msgs or []
        db.search_summaries.return_value = sums or []
        return db

    def test_returns_messages_and_summaries(self):
        """Should return both message and summary results."""
        db = self._make_mock_db(
            msgs=[{"message_id": "m1", "content": "hello", "created_at": "2024-01-01"}],
            sums=[{"summary_id": "s1", "content": "world", "created_at": "2024-01-02"}],
        )
        retriever = HybridRetriever(db=db)
        results = retriever._fts_search("test")
        assert len(results) == 2
        types = [r["target_type"] for r in results]
        assert "message" in types
        assert "summary" in types

    def test_includes_content_and_created_at(self):
        """Results should include content and created_at."""
        db = self._make_mock_db(
            msgs=[{"message_id": "m1", "content": "hello", "created_at": "2024-01-01"}],
        )
        retriever = HybridRetriever(db=db)
        results = retriever._fts_search("test")
        assert results[0]["content"] == "hello"
        assert results[0]["created_at"] == "2024-01-01"

    def test_passes_conversation_id(self):
        """Should pass conversation_id to both search methods."""
        db = self._make_mock_db()
        retriever = HybridRetriever(db=db)
        retriever._fts_search("test", conversation_id="conv_123")
        db.search_messages.assert_called_once_with(
            "test", conversation_id="conv_123", limit=50
        )
        db.search_summaries.assert_called_once_with(
            "test", conversation_id="conv_123", limit=50
        )

    def test_empty_results(self):
        """Should return empty list when no matches."""
        db = self._make_mock_db()
        retriever = HybridRetriever(db=db)
        results = retriever._fts_search("nonexistent")
        assert results == []

    def test_rank_values(self):
        """Messages and summaries should each have independent rank sequences."""
        db = self._make_mock_db(
            msgs=[
                {"message_id": "m1", "content": "a", "created_at": ""},
                {"message_id": "m2", "content": "b", "created_at": ""},
            ],
            sums=[
                {"summary_id": "s1", "content": "c", "created_at": ""},
            ],
        )
        retriever = HybridRetriever(db=db)
        results = retriever._fts_search("test")
        msg_results = [r for r in results if r["target_type"] == "message"]
        assert msg_results[0]["rank"] == 0
        assert msg_results[1]["rank"] == 1
        sum_results = [r for r in results if r["target_type"] == "summary"]
        assert sum_results[0]["rank"] == 0


class TestVectorSearch:
    """Tests for _vector_search method."""

    def test_returns_empty_when_no_embedder(self):
        """Should return empty list when no embedder is set."""
        db = MagicMock()
        retriever = HybridRetriever(db=db, embedder=None)
        results = retriever._vector_search("test")
        assert results == []

    def test_returns_empty_when_embedder_not_available(self):
        """Should return empty list when embedder.is_available() returns False."""
        db = MagicMock()
        embedder = MagicMock()
        embedder.is_available.return_value = False
        retriever = HybridRetriever(db=db, embedder=embedder)
        results = retriever._vector_search("test")
        assert results == []

    def test_maps_fields_correctly(self):
        """Should correctly map vector search results to expected format."""
        db = MagicMock()
        db.vector_search.return_value = [
            {"target_id": "v1", "target_type": "message", "score": 0.95},
            {"target_id": "v2", "target_type": "summary", "score": 0.80},
        ]
        embedder = MagicMock()
        embedder.is_available.return_value = True
        embedder.embed.return_value = [0.1] * 1024
        retriever = HybridRetriever(db=db, embedder=embedder)
        results = retriever._vector_search("query")
        assert len(results) == 2
        assert results[0]["target_id"] == "v1"
        assert results[0]["target_type"] == "message"
        assert results[0]["score"] == 0.95
        assert results[0]["content"] == ""
        assert results[0]["source"] == "vector"

    def test_passes_conversation_id_to_vector_search(self):
        """Should pass conversation_id to db.vector_search."""
        db = MagicMock()
        db.vector_search.return_value = []
        embedder = MagicMock()
        embedder.is_available.return_value = True
        embedder.embed.return_value = [0.1] * 1024
        retriever = HybridRetriever(db=db, embedder=embedder)
        retriever._vector_search("query", conversation_id="conv_1")
        db.vector_search.assert_called_once_with(
            [0.1] * 1024, top_k=50, conversation_id="conv_1"
        )


class TestFullPipeline:
    """Tests for the full search() pipeline."""

    def _make_retriever(
        self, with_embedder=False, msgs=None, sums=None, vec_results=None
    ):
        db = MagicMock()
        db.search_messages.return_value = msgs or []
        db.search_summaries.return_value = sums or []
        db.vector_search.return_value = vec_results or []

        embedder = None
        if with_embedder:
            embedder = MagicMock()
            embedder.is_available.return_value = True
            embedder.embed.return_value = [0.1] * 1024

        return HybridRetriever(db=db, embedder=embedder)

    def test_fts_only_when_no_embedder(self):
        """Should work with FTS-only when no embedder is available."""
        retriever = self._make_retriever(
            with_embedder=False,
            msgs=[
                {
                    "message_id": "m1",
                    "content": "hello world",
                    "created_at": datetime.utcnow().isoformat(),
                }
            ],
        )
        results = retriever.search("hello", top_k=10, min_score=0.0)
        assert len(results) >= 1
        assert results[0]["target_id"] == "m1"

    def test_both_fts_and_vector(self):
        """Should use both FTS and vector when embedder is available."""
        retriever = self._make_retriever(
            with_embedder=True,
            msgs=[
                {
                    "message_id": "m1",
                    "content": "hello",
                    "created_at": datetime.utcnow().isoformat(),
                }
            ],
            vec_results=[{"target_id": "v1", "target_type": "message", "score": 0.9}],
        )
        results = retriever.search("hello", top_k=10, min_score=0.0)
        target_ids = [r["target_id"] for r in results]
        assert "m1" in target_ids or "v1" in target_ids

    def test_results_sorted_by_normalized_score_descending(self):
        """Results should be sorted by normalized_score in descending order."""
        now = datetime.utcnow().isoformat()
        retriever = self._make_retriever(
            with_embedder=False,
            msgs=[
                {"message_id": "m1", "content": "alpha", "created_at": now},
                {"message_id": "m2", "content": "beta", "created_at": now},
                {"message_id": "m3", "content": "gamma", "created_at": now},
            ],
        )
        results = retriever.search("alpha beta gamma", top_k=10, min_score=0.0)
        scores = [r["normalized_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_respects_top_k(self):
        """Should not return more than top_k results."""
        now = datetime.utcnow().isoformat()
        retriever = self._make_retriever(
            with_embedder=False,
            msgs=[
                {"message_id": f"m{i}", "content": f"content {i}", "created_at": now}
                for i in range(10)
            ],
        )
        results = retriever.search("content", top_k=3, min_score=0.0)
        assert len(results) <= 3

    def test_respects_min_score(self):
        """Should filter out results below min_score."""
        retriever = self._make_retriever(
            with_embedder=True,
            vec_results=[
                {"target_id": "v1", "target_type": "message", "score": 0.9},
                {"target_id": "v2", "target_type": "message", "score": 0.1},
            ],
        )
        results = retriever.search("test", top_k=10, min_score=0.5)
        for r in results:
            assert r["normalized_score"] >= 0.5

    def test_empty_query_returns_empty(self):
        """Should handle empty results gracefully."""
        retriever = self._make_retriever(with_embedder=False)
        results = retriever.search("nonexistent query", top_k=5)
        assert results == []

    def test_normalized_score_max_is_one(self):
        """Top result should have normalized_score == 1.0."""
        now = datetime.utcnow().isoformat()
        retriever = self._make_retriever(
            with_embedder=False,
            msgs=[
                {
                    "message_id": "m1",
                    "content": "unique content alpha",
                    "created_at": now,
                },
            ],
        )
        results = retriever.search("unique", top_k=10, min_score=0.0)
        if results:
            assert abs(results[0]["normalized_score"] - 1.0) < 1e-6
