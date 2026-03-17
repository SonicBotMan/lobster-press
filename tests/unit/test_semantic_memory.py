"""
Unit tests for semantic memory module.
"""
import pytest
import tempfile
import os


class TestSemanticMemory:
    """Tests for SemanticMemory class."""

    def test_import(self):
        """Should be able to import SemanticMemory."""
        from src.semantic_memory import SemanticMemory
        assert SemanticMemory is not None

    def test_init_with_db(self, temp_db):
        """Should initialize with database."""
        from src.semantic_memory import SemanticMemory
        memory = SemanticMemory(temp_db)
        assert memory is not None

    def test_get_active_notes_returns_list(self, temp_db):
        """get_active_notes should return a list."""
        from src.semantic_memory import SemanticMemory
        memory = SemanticMemory(temp_db)
        notes = memory.get_active_notes(conversation_id="conv_123")
        assert isinstance(notes, list)

    def test_format_for_context_returns_string(self, temp_db):
        """format_for_context should return a string."""
        from src.semantic_memory import SemanticMemory
        memory = SemanticMemory(temp_db)
        formatted = memory.format_for_context([])
        assert isinstance(formatted, str)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    from src.database import LobsterDatabase
    db = LobsterDatabase(db_path)
    yield db
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
