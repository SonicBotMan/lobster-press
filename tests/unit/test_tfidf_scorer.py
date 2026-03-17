"""
Unit tests for TF-IDF scorer module.
"""
import pytest


class TestTFIDFScorer:
    """Tests for TFIDFScorer class."""

    def test_import(self):
        """Should be able to import TFIDFScorer."""
        from src.pipeline.tfidf_scorer import TFIDFScorer
        assert TFIDFScorer is not None

    def test_init(self):
        """Should initialize without errors."""
        from src.pipeline.tfidf_scorer import TFIDFScorer
        scorer = TFIDFScorer()
        assert scorer is not None

    def test_score_and_tag_returns_list(self):
        """score_and_tag should return a list of ScoredMessage."""
        from src.pipeline.tfidf_scorer import TFIDFScorer
        scorer = TFIDFScorer()
        messages = [
            {"id": "1", "content": "test message 1"},
            {"id": "2", "content": "test message 2"},
        ]
        result = scorer.score_and_tag(messages)
        assert isinstance(result, list)

    def test_score_messages_returns_list(self):
        """score_messages should return a list of ScoredMessage."""
        from src.pipeline.tfidf_scorer import TFIDFScorer
        scorer = TFIDFScorer()
        messages = [
            {"id": "1", "content": "database configuration"},
            {"id": "2", "content": "system setup"},
        ]
        result = scorer.score_messages(messages)
        assert isinstance(result, list)

    def test_tokenize_returns_list(self):
        """tokenize should return a list of tokens."""
        from src.pipeline.tfidf_scorer import TFIDFScorer
        scorer = TFIDFScorer()
        tokens = scorer.tokenize("test message here")
        assert isinstance(tokens, list)
