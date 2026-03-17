"""
Unit tests for event segmenter module.
"""
import pytest
from src.pipeline.event_segmenter import EventSegmenter


class TestEventSegmenter:
    """Tests for EventSegmenter class."""

    def test_segment_returns_list(self):
        """Segment should return a list of episodes."""
        segmenter = EventSegmenter()
        messages = [
            {"id": "1", "content": "message 1", "timestamp": "2026-03-17T10:00:00Z"},
            {"id": "2", "content": "message 2", "timestamp": "2026-03-17T10:01:00Z"},
        ]
        episodes = segmenter.segment(messages)
        assert isinstance(episodes, list)

    def test_temporal_gap_creates_new_episode(self):
        """Large temporal gap should create new episode."""
        segmenter = EventSegmenter(temporal_gap_hours=1.0)
        messages = [
            {"id": "1", "content": "message 1", "timestamp": "2026-03-17T10:00:00Z"},
            {"id": "2", "content": "message 2", "timestamp": "2026-03-17T12:00:00Z"},  # 2 hour gap
        ]
        episodes = segmenter.segment(messages)
        assert len(episodes) == 2

    def test_system_message_creates_new_episode(self):
        """System messages should create new episode."""
        segmenter = EventSegmenter()
        messages = [
            {"id": "1", "role": "user", "content": "message 1", "timestamp": "2026-03-17T10:00:00Z"},
            {"id": "2", "role": "system", "content": "system message", "timestamp": "2026-03-17T10:01:00Z"},
            {"id": "3", "role": "user", "content": "message 3", "timestamp": "2026-03-17T10:02:00Z"},
        ]
        episodes = segmenter.segment(messages)
        assert len(episodes) == 2

    def test_empty_messages_returns_empty_list(self):
        """Empty messages should return empty list."""
        segmenter = EventSegmenter()
        episodes = segmenter.segment([])
        assert episodes == []

    def test_single_message_creates_one_episode(self):
        """Single message should create one episode."""
        segmenter = EventSegmenter()
        messages = [
            {"id": "1", "content": "single message", "timestamp": "2026-03-17T10:00:00Z"},
        ]
        episodes = segmenter.segment(messages)
        assert len(episodes) == 1
