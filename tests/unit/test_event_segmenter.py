"""
Unit tests for event segmenter module.
"""
import pytest


class TestEventSegmenter:
    """Tests for EventSegmenter class."""

    def test_import(self):
        """Should be able to import EventSegmenter."""
        from src.pipeline.event_segmenter import EventSegmenter
        assert EventSegmenter is not None

    def test_init(self):
        """Should initialize without errors."""
        from src.pipeline.event_segmenter import EventSegmenter
        segmenter = EventSegmenter()
        assert segmenter is not None

    def test_segment_returns_list(self):
        """segment should return a list of episodes."""
        from src.pipeline.event_segmenter import EventSegmenter
        segmenter = EventSegmenter()
        messages = [
            {"id": "1", "content": "message 1", "timestamp": "2026-03-17T10:00:00Z"},
            {"id": "2", "content": "message 2", "timestamp": "2026-03-17T10:01:00Z"},
        ]
        episodes = segmenter.segment(messages)
        assert isinstance(episodes, list)

    def test_empty_messages_returns_empty_list(self):
        """Empty messages should return empty list."""
        from src.pipeline.event_segmenter import EventSegmenter
        segmenter = EventSegmenter()
        episodes = segmenter.segment([])
        assert episodes == []

    def test_single_message_creates_one_episode(self):
        """Single message should create one episode."""
        from src.pipeline.event_segmenter import EventSegmenter
        segmenter = EventSegmenter()
        messages = [
            {"id": "1", "content": "single message", "timestamp": "2026-03-17T10:00:00Z"},
        ]
        episodes = segmenter.segment(messages)
        assert len(episodes) == 1
