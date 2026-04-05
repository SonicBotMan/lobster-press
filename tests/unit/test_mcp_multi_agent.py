"""
Unit tests for MCP Multi-Agent Tools (Phase 3.2).
Tests: lobster_memory_write_public, lobster_skill_search,
lobster_skill_publish, lobster_skill_unpublish
"""

import pytest
import asyncio
import hashlib
from datetime import datetime


def run_async(coro):
    """Run an async coroutine."""
    return asyncio.run(coro)


class TestMultiAgentToolRegistration:
    """Tests for tool registration."""

    def test_all_four_tools_registered(self):
        """All 4 multi-agent tools should be registered."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        tool_names = [t.name for t in server.tools]

        assert "lobster_memory_write_public" in tool_names
        assert "lobster_skill_search" in tool_names
        assert "lobster_skill_publish" in tool_names
        assert "lobster_skill_unpublish" in tool_names

    def test_memory_write_public_schema(self):
        """lobster_memory_write_public should have correct input_schema."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        tool = next(t for t in server.tools if t.name == "lobster_memory_write_public")

        assert tool.input_schema["type"] == "object"
        assert "content" in tool.input_schema["properties"]
        assert "summary" in tool.input_schema["properties"]
        assert "conversation_id" in tool.input_schema["properties"]
        assert "content" in tool.input_schema["required"]

    def test_skill_search_schema(self):
        """lobster_skill_search should have correct input_schema."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        tool = next(t for t in server.tools if t.name == "lobster_skill_search")

        assert tool.input_schema["type"] == "object"
        assert "query" in tool.input_schema["properties"]
        assert "scope" in tool.input_schema["properties"]
        assert "limit" in tool.input_schema["properties"]
        assert tool.input_schema["properties"]["scope"]["enum"] == [
            "mix",
            "self",
            "public",
        ]

    def test_skill_publish_schema(self):
        """lobster_skill_publish should have correct input_schema."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        tool = next(t for t in server.tools if t.name == "lobster_skill_publish")

        assert tool.input_schema["type"] == "object"
        assert "skill_id" in tool.input_schema["properties"]
        assert "skill_id" in tool.input_schema["required"]

    def test_skill_unpublish_schema(self):
        """lobster_skill_unpublish should have correct input_schema."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        tool = next(t for t in server.tools if t.name == "lobster_skill_unpublish")

        assert tool.input_schema["type"] == "object"
        assert "skill_id" in tool.input_schema["properties"]
        assert "skill_id" in tool.input_schema["required"]


class TestHandleMemoryWritePublic:
    """Tests for _handle_memory_write_public."""

    def test_saves_message_with_owner_public(self, temp_db):
        """Should save message with owner='public'."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        content = "Test public memory content"
        result = run_async(server._handle_memory_write_public({"content": content}))

        assert result["status"] == "ok"
        assert result["owner"] == "public"
        assert "message_id" in result
        assert result["message_id"].startswith("pub_")

    def test_returns_message_id_and_status(self, temp_db):
        """Should return message_id and status."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        content = "Another public memory"
        result = run_async(server._handle_memory_write_public({"content": content}))

        assert "status" in result
        assert "message_id" in result
        assert result["status"] == "ok"

    def test_saves_with_summary(self, temp_db):
        """Should save with optional summary."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        content = "Memory with summary"
        summary = "This is a summary"
        result = run_async(
            server._handle_memory_write_public({"content": content, "summary": summary})
        )

        assert result["status"] == "ok"

        temp_db.cursor.execute(
            "SELECT metadata FROM messages WHERE message_id = ?",
            (result["message_id"],),
        )
        row = temp_db.cursor.fetchone()
        assert row is not None
        import json

        stored_message = json.loads(row[0])
        assert stored_message["summary"] == summary
        assert stored_message["public"] is True

    def test_saves_with_conversation_id(self, temp_db):
        """Should save with specified conversation_id."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        content = "Memory for specific conversation"
        conv_id = "conv_specific_123"
        result = run_async(
            server._handle_memory_write_public(
                {"content": content, "conversation_id": conv_id}
            )
        )

        assert result["status"] == "ok"

        temp_db.cursor.execute(
            "SELECT conversation_id FROM messages WHERE message_id = ?",
            (result["message_id"],),
        )
        row = temp_db.cursor.fetchone()
        assert row is not None
        assert row[0] == conv_id


class TestHandleSkillSearch:
    """Tests for _handle_skill_search."""

    def test_scope_self_returns_only_own_skills(self, temp_db):
        """scope='self' should return only own skills."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        temp_db.cursor.execute("""
            INSERT INTO skills (skill_id, name, owner, visibility, created_at, updated_at)
            VALUES ('skill_self_1', 'My Skill', 'default', 'private', datetime('now'), datetime('now'))
        """)
        temp_db.cursor.execute("""
            INSERT INTO skills (skill_id, name, owner, visibility, created_at, updated_at)
            VALUES ('skill_pub_1', 'Public Skill', 'public', 'public', datetime('now'), datetime('now'))
        """)
        temp_db.conn.commit()

        result = run_async(server._handle_skill_search({"query": "*", "scope": "self"}))

        assert result["scope"] == "self"
        assert all(s["owner"] == "default" for s in result["skills"])

    def test_scope_public_returns_only_public_skills(self, temp_db):
        """scope='public' should return only public skills."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        temp_db.cursor.execute("""
            INSERT INTO skills (skill_id, name, owner, visibility, created_at, updated_at)
            VALUES ('skill_private', 'Private Skill', 'default', 'private', datetime('now'), datetime('now'))
        """)
        temp_db.cursor.execute("""
            INSERT INTO skills (skill_id, name, owner, visibility, created_at, updated_at)
            VALUES ('skill_public', 'Public Skill', 'someone', 'public', datetime('now'), datetime('now'))
        """)
        temp_db.conn.commit()

        result = run_async(
            server._handle_skill_search({"query": "*", "scope": "public"})
        )

        assert result["scope"] == "public"
        assert all(s["visibility"] == "public" for s in result["skills"])

    def test_scope_mix_calls_search_skills(self, temp_db):
        """scope='mix' should call search_skills."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        temp_db.cursor.execute("""
            INSERT INTO skills (skill_id, name, owner, visibility, created_at, updated_at)
            VALUES ('skill_mix', 'Mix Skill', 'default', 'public', datetime('now'), datetime('now'))
        """)
        temp_db.conn.commit()

        result = run_async(
            server._handle_skill_search({"query": "Mix", "scope": "mix"})
        )

        assert result["scope"] == "mix"
        assert "skills" in result

    def test_respects_limit(self, temp_db):
        """Should respect limit parameter."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        for i in range(5):
            temp_db.cursor.execute(
                """
                INSERT INTO skills (skill_id, name, owner, visibility, created_at, updated_at)
                VALUES (?, ?, 'default', 'public', datetime('now'), datetime('now'))
            """,
                (f"skill_limit_{i}", f"Skill {i}"),
            )
        temp_db.conn.commit()

        result = run_async(
            server._handle_skill_search({"query": "*", "scope": "public", "limit": 3})
        )

        assert len(result["skills"]) <= 3


class TestHandleSkillPublish:
    """Tests for _handle_skill_publish."""

    def test_updates_visibility_to_public(self, temp_db):
        """Should update visibility to 'public'."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        temp_db.cursor.execute("""
            INSERT INTO skills (skill_id, name, owner, visibility, created_at, updated_at)
            VALUES ('skill_pub_test', 'Test Skill', 'default', 'private', datetime('now'), datetime('now'))
        """)
        temp_db.conn.commit()

        result = run_async(
            server._handle_skill_publish(
                {"skill_id": "skill_pub_test"}, visibility="public"
            )
        )

        assert result["status"] == "ok"
        assert result["visibility"] == "public"

        temp_db.cursor.execute(
            "SELECT visibility FROM skills WHERE skill_id = ?", ("skill_pub_test",)
        )
        row = temp_db.cursor.fetchone()
        assert row[0] == "public"

    def test_updates_visibility_to_private(self, temp_db):
        """Should update visibility to 'private'."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        temp_db.cursor.execute("""
            INSERT INTO skills (skill_id, name, owner, visibility, created_at, updated_at)
            VALUES ('skill_priv_test', 'Test Skill', 'default', 'public', datetime('now'), datetime('now'))
        """)
        temp_db.conn.commit()

        result = run_async(
            server._handle_skill_publish(
                {"skill_id": "skill_priv_test"}, visibility="private"
            )
        )

        assert result["status"] == "ok"
        assert result["visibility"] == "private"

    def test_returns_error_when_skill_id_missing(self, temp_db):
        """Should return error when skill_id is missing."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        result = run_async(server._handle_skill_publish({}, visibility="public"))

        assert "error" in result
        assert "skill_id is required" in result["error"]

    def test_returns_error_when_skill_not_found(self, temp_db):
        """Should return error when skill not found."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        result = run_async(
            server._handle_skill_publish(
                {"skill_id": "nonexistent_skill"}, visibility="public"
            )
        )

        assert "error" in result
        assert "Skill not found" in result["error"]
