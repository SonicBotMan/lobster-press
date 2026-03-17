"""
Unit tests for TF-IDF scorer module.
"""
import pytest
from src.pipeline.tfidf_scorer import TFIDFScorer, classify_message_type


class TestTFIDFScorer:
    """Tests for TFIDFScorer class."""

    def test_score_returns_float(self):
        """Score should return a float value."""
        scorer = TFIDFScorer()
        score = scorer.score("test message", ["doc1", "doc2", "doc3"])
        assert isinstance(score, float)

    def test_score_range(self):
        """Score should be between 0 and 1."""
        scorer = TFIDFScorer()
        score = scorer.score("database configuration", ["PostgreSQL", "MySQL", "MongoDB"])
        assert 0.0 <= score <= 1.0

    def test_high_frequency_lower_score(self):
        """High frequency words should get lower scores."""
        scorer = TFIDFScorer()
        # Common word in all documents
        score_common = scorer.score("the", ["the database", "the config", "the system"])
        # Rare word in one document
        score_rare = scorer.score("PostgreSQL", ["the database", "MySQL config", "MongoDB system"])
        assert score_rare > score_common

    def test_empty_message(self):
        """Empty message should return 0."""
        scorer = TFIDFScorer()
        score = scorer.score("", ["doc1", "doc2"])
        assert score == 0.0

    def test_no_documents(self):
        """No documents should return 0."""
        scorer = TFIDFScorer()
        score = scorer.score("test message", [])
        assert score == 0.0


class TestClassifyMessageType:
    """Tests for classify_message_type function."""

    def test_decision_type(self):
        """Messages with decision keywords should be classified as decision."""
        msg_type = classify_message_type("我们决定使用 PostgreSQL")
        assert msg_type == "decision"

    def test_code_type(self):
        """Messages with code blocks should be classified as code."""
        msg_type = classify_message_type("```python\nprint('hello')\n```")
        assert msg_type == "code"

    def test_config_type(self):
        """Messages with config keywords should be classified as config."""
        msg_type = classify_message_type("配置文件路径是 /etc/app/config.yaml")
        assert msg_type == "config"

    def test_error_type(self):
        """Messages with error keywords should be classified as error."""
        msg_type = classify_message_type("Error: ECONNREFUSED")
        assert msg_type == "error"

    def test_chitchat_type(self):
        """Casual messages should be classified as chitchat."""
        msg_type = classify_message_type("好的，明白了")
        assert msg_type == "chitchat"
