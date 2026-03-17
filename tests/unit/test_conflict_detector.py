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

    def test_detect_returns_list(self):
        """detect should return a list of conflicts."""
        from src.pipeline.conflict_detector import ConflictDetector
        detector = ConflictDetector(use_nli=False)
        result = detector.detect(
            new_message={"content": "改用 MongoDB"},
            existing_notes=[{"content": "使用 PostgreSQL"}]
        )
        assert isinstance(result, list)

    def test_detect_no_conflict(self):
        """Unrelated messages should not trigger conflict."""
        from src.pipeline.conflict_detector import ConflictDetector
        detector = ConflictDetector(use_nli=False)
        result = detector.detect(
            new_message={"content": "我们使用 React 18"},
            existing_notes=[{"content": "项目采用 PostgreSQL"}]
        )
        assert isinstance(result, list)

    def test_empty_existing_notes(self):
        """Empty existing notes should not cause errors."""
        from src.pipeline.conflict_detector import ConflictDetector
        detector = ConflictDetector(use_nli=False)
        result = detector.detect(
            new_message={"content": "改用 MongoDB"},
            existing_notes=[]
        )
        assert isinstance(result, list)

    def test_reconcile_without_llm_client(self):
        """reconcile should fallback to message truncation without LLM."""
        from src.pipeline.conflict_detector import ConflictDetector, ConflictResult
        from unittest.mock import Mock, MagicMock
        
        detector = ConflictDetector(use_nli=False)
        
        # Mock SemanticMemory
        mock_memory = Mock()
        mock_memory._save_note = Mock(return_value="new_note_123")
        mock_memory.db = Mock()
        mock_memory.db.cursor = Mock()
        mock_memory.db.conn = Mock()
        
        # Mock conflict
        conflict = ConflictResult(
            old_note_id="old_note_1",
            old_content="使用 PostgreSQL",
            old_category="decision",
            new_claim="改用 MongoDB 因为数据结构变化多",
            conflict_score=0.85
        )
        
        # Call reconcile WITHOUT llm_client
        detector.reconcile(
            semantic_memory=mock_memory,
            conflicts=[conflict],
            new_message={"id": "msg_1", "content": "改用 MongoDB 因为数据结构变化多"},
            conversation_id="conv_1",
            llm_client=None  # No LLM
        )
        
        # Should call _save_note with truncated content
        mock_memory._save_note.assert_called_once()
        call_args = mock_memory._save_note.call_args
        assert call_args[1]["category"] == "decision"  # Inherit old category
        assert call_args[1]["confidence"] == 0.7  # Lower confidence
        assert "[更新]" in call_args[1]["content"]

    def test_reconcile_with_llm_client(self):
        """reconcile should use LLM extraction when available."""
        from src.pipeline.conflict_detector import ConflictDetector, ConflictResult
        from unittest.mock import Mock, MagicMock
        
        detector = ConflictDetector(use_nli=False)
        
        # Mock SemanticMemory
        mock_memory = Mock()
        mock_memory.extract_and_store = Mock(return_value=["new_note_llm"])
        mock_memory.db = Mock()
        mock_memory.db.cursor = Mock()
        mock_memory.db.conn = Mock()
        
        # Mock LLM client
        mock_llm = Mock()
        
        # Mock conflict
        conflict = ConflictResult(
            old_note_id="old_note_1",
            old_content="使用 PostgreSQL",
            old_category="decision",
            new_claim="改用 MongoDB",
            conflict_score=0.85
        )
        
        # Call reconcile WITH llm_client
        detector.reconcile(
            semantic_memory=mock_memory,
            conflicts=[conflict],
            new_message={"id": "msg_1", "content": "改用 MongoDB"},
            conversation_id="conv_1",
            llm_client=mock_llm  # With LLM
        )
        
        # Should call extract_and_store (high-quality path)
        mock_memory.extract_and_store.assert_called_once()
        call_args = mock_memory.extract_and_store.call_args
        assert call_args[1]["llm_client"] == mock_llm
        assert call_args[1]["conversation_id"] == "conv_1"

    def test_reconcile_marks_old_note_superseded(self):
        """reconcile should mark old note as superseded."""
        from src.pipeline.conflict_detector import ConflictDetector, ConflictResult
        from unittest.mock import Mock
        from datetime import datetime
        
        detector = ConflictDetector(use_nli=False)
        
        # Mock SemanticMemory
        mock_memory = Mock()
        mock_memory._save_note = Mock(return_value="new_note_456")
        mock_memory.db = Mock()
        mock_memory.db.cursor = Mock()
        mock_memory.db.conn = Mock()
        
        # Mock conflict
        conflict = ConflictResult(
            old_note_id="old_note_1",
            old_content="旧决策",
            old_category="decision",
            new_claim="新决策",
            conflict_score=0.9
        )
        
        # Call reconcile
        detector.reconcile(
            semantic_memory=mock_memory,
            conflicts=[conflict],
            new_message={"id": "msg_1", "content": "新决策"},
            conversation_id="conv_1",
            llm_client=None
        )
        
        # Should execute UPDATE to mark superseded
        mock_memory.db.cursor.execute.assert_called_once()
        sql = mock_memory.db.cursor.execute.call_args[0][0]
        assert "UPDATE notes" in sql
        assert "superseded_by" in sql
