"""
Unit tests for semantic memory module.
"""
import pytest
from src.semantic_memory import SemanticMemory


class TestSemanticMemory:
    """Tests for SemanticMemory class."""

    def test_extract_and_store_returns_list(self, temp_db, mock_llm):
        """Extract and store should return list of notes."""
        memory = SemanticMemory(temp_db, llm_client=mock_llm)
        messages = [
            {"id": "1", "content": "我们决定使用 PostgreSQL", "role": "user"}
        ]
        notes = memory.extract_and_store(messages, conversation_id="conv_123")
        assert isinstance(notes, list)

    def test_get_active_notes_returns_list(self, temp_db):
        """Get active notes should return a list."""
        memory = SemanticMemory(temp_db)
        notes = memory.get_active_notes(conversation_id="conv_123")
        assert isinstance(notes, list)

    def test_format_for_context_returns_string(self, temp_db):
        """Format for context should return a string."""
        memory = SemanticMemory(temp_db)
        formatted = memory.format_for_context(conversation_id="conv_123")
        assert isinstance(formatted, str)

    def test_deduplication(self, temp_db, mock_llm):
        """Duplicate content should not be inserted twice."""
        memory = SemanticMemory(temp_db, llm_client=mock_llm)

        # Insert same content twice
        memory.extract_and_store(
            [{"id": "1", "content": "使用 PostgreSQL"}],
            conversation_id="conv_123"
        )
        memory.extract_and_store(
            [{"id": "2", "content": "使用 PostgreSQL"}],
            conversation_id="conv_123"
        )

        # Should only have one note
        notes = memory.get_active_notes(conversation_id="conv_123")
        # Check that we don't have duplicate content
        contents = [n.get("content") for n in notes]
        # Allow for some variation, but not exact duplicates
        assert len(contents) == len(set(contents))

    def test_superseded_notes_not_active(self, temp_db):
        """Superseded notes should not appear in active notes."""
        memory = SemanticMemory(temp_db)

        # Manually insert a note and mark as superseded
        temp_db.execute(
            """INSERT INTO notes
               (note_id, conversation_id, category, content, confidence, created_at, updated_at, superseded_by)
               VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?)""",
            ("note_001", "conv_123", "decision", "旧决定", 0.9, "note_002")
        )

        notes = memory.get_active_notes(conversation_id="conv_123")
        # Superseded note should not be in active notes
        note_ids = [n.get("note_id") for n in notes]
        assert "note_001" not in note_ids

    def test_confidence_threshold(self, temp_db, mock_llm):
        """Notes below confidence threshold should be filtered."""
        memory = SemanticMemory(temp_db, llm_client=mock_llm, min_confidence=0.7)

        # Mock LLM would return notes with various confidence levels
        # The system should filter based on min_confidence
        # This is a placeholder test - actual implementation depends on mock
        pass
