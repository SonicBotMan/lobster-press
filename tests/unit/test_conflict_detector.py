"""
Unit tests for conflict detector module.
"""
import pytest


class TestConflictDetector:
    """Tests for ConflictDetector class."""

    def test_import(self):
        """Should be able to import ConflictDetector."""
        from src.pipeline.conflict_detector import ConflictDetector
        assert ConflictDetector is not None

    def test_init(self):
        """Should initialize without errors."""
        from src.pipeline.conflict_detector import ConflictDetector
        detector = ConflictDetector(use_nli=False)
        assert detector is not None

    def test_detect_returns_dict(self):
        """detect should return a dict."""
        from src.pipeline.conflict_detector import ConflictDetector
        detector = ConflictDetector(use_nli=False)
        result = detector.detect(
            new_message="改用 MongoDB",
            existing_notes=[{"content": "使用 PostgreSQL"}]
        )
        assert isinstance(result, dict)

    def test_detect_no_conflict(self):
        """Unrelated messages should not trigger conflict."""
        from src.pipeline.conflict_detector import ConflictDetector
        detector = ConflictDetector(use_nli=False)
        result = detector.detect(
            new_message="我们使用 React 18",
            existing_notes=[{"content": "项目采用 PostgreSQL"}]
        )
        assert isinstance(result, dict)

    def test_empty_existing_notes(self):
        """Empty existing notes should not cause errors."""
        from src.pipeline.conflict_detector import ConflictDetector
        detector = ConflictDetector(use_nli=False)
        result = detector.detect(
            new_message="改用 MongoDB",
            existing_notes=[]
        )
        assert isinstance(result, dict)
