"""
Pytest configuration and shared fixtures for LobsterPress tests.
"""
import pytest
import tempfile
import os
from pathlib import Path

from src.database import LobsterDatabase
from src.llm_client import MockLLMClient


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = LobsterDatabase(db_path)
    yield db
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def mock_llm():
    """Create a mock LLM client for testing."""
    return MockLLMClient()


@pytest.fixture
def sample_messages():
    """Sample messages for testing."""
    return [
        {
            "id": "msg_001",
            "role": "user",
            "content": "我们决定使用 PostgreSQL 作为主数据库",
            "timestamp": "2026-03-17T10:00:00Z"
        },
        {
            "id": "msg_002",
            "role": "assistant",
            "content": "好的，我会记住这个决定。PostgreSQL 是一个可靠的选择，特别是对于需要 ACID 事务的场景。",
            "timestamp": "2026-03-17T10:01:00Z"
        },
        {
            "id": "msg_003",
            "role": "user",
            "content": "另外，我们采用 React 18 作为前端框架",
            "timestamp": "2026-03-17T10:02:00Z"
        },
        {
            "id": "msg_004",
            "role": "assistant",
            "content": "明白了。React 18 带来了很多新特性，比如并发渲染和自动批处理。",
            "timestamp": "2026-03-17T10:03:00Z"
        },
        {
            "id": "msg_005",
            "role": "user",
            "content": "改用 MongoDB，因为需要文档灵活性",
            "timestamp": "2026-03-17T10:05:00Z"
        }
    ]


@pytest.fixture
def sample_notes():
    """Sample notes for testing."""
    return [
        {
            "note_id": "note_001",
            "conversation_id": "conv_123",
            "category": "decision",
            "content": "项目采用 PostgreSQL 作为主数据库",
            "confidence": 0.95
        },
        {
            "note_id": "note_002",
            "conversation_id": "conv_123",
            "category": "decision",
            "content": "前端使用 React 18",
            "confidence": 0.90
        }
    ]
