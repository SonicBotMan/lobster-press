"""
Unit tests for lobster_skill MCP tool.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch


class TestLobsterSkillToolRegistration:
    """Tests for lobster_skill tool registration."""

    def test_lobster_skill_in_tools(self):
        """lobster_skill should be registered in tools list."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        tool_names = [t.name for t in server.tools]

        assert "lobster_skill" in tool_names

    def test_lobster_skill_input_schema(self):
        """lobster_skill should have correct input_schema."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        tool = next(t for t in server.tools if t.name == "lobster_skill")

        assert tool.input_schema["type"] == "object"
        assert "action" in tool.input_schema["properties"]
        assert tool.input_schema["properties"]["action"]["enum"] == [
            "get",
            "install",
            "list",
        ]
        assert "skill_id" in tool.input_schema["properties"]
        assert "conversation_id" in tool.input_schema["properties"]
        assert "task_goal" in tool.input_schema["properties"]
        assert "action" in tool.input_schema["required"]


def run_async(coro):
    """Run an async coroutine."""
    return asyncio.run(coro)


class TestLobsterSkillGetAction:
    """Tests for lobster_skill get action."""

    def test_get_returns_skill_when_exists(self, temp_db):
        """get action should return skill when skill_id exists."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        skill_id = "skill_test_123"
        temp_db.cursor.execute(
            """
            INSERT INTO skills (skill_id, name, owner, visibility, created_at, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
            (skill_id, "Test Skill", "default", "private"),
        )
        temp_db.conn.commit()

        temp_db.cursor.execute(
            """
            INSERT INTO skill_versions (skill_id, version, content, quality_score, created_at)
            VALUES (?, 1, '# Test Content', 0.8, datetime('now'))
        """,
            (skill_id,),
        )
        temp_db.conn.commit()

        result = run_async(
            server._handle_lobster_skill({"action": "get", "skill_id": skill_id})
        )

        assert "skill" in result
        assert result["skill"]["skill_id"] == skill_id
        assert result["content"] == "# Test Content"
        assert result["quality_score"] == 0.8

    def test_get_returns_error_when_skill_id_missing(self):
        """get action should return error when skill_id is missing."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()

        result = run_async(server._handle_lobster_skill({"action": "get"}))

        assert "error" in result
        assert "skill_id is required" in result["error"]

    def test_get_returns_error_when_skill_not_found(self):
        """get action should return error when skill not found."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()

        result = run_async(
            server._handle_lobster_skill(
                {"action": "get", "skill_id": "nonexistent_skill"}
            )
        )

        assert "error" in result
        assert "Skill not found" in result["error"]


class TestLobsterSkillListAction:
    """Tests for lobster_skill list action."""

    def test_list_returns_all_skills(self, temp_db):
        """list action should return all skills when no filter."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        temp_db.cursor.execute("""
            INSERT INTO skills (skill_id, name, owner, visibility, created_at, updated_at)
            VALUES ('skill_list_1', 'Skill 1', 'default', 'private', datetime('now'), datetime('now'))
        """)
        temp_db.cursor.execute("""
            INSERT INTO skills (skill_id, name, owner, visibility, created_at, updated_at)
            VALUES ('skill_list_2', 'Skill 2', 'default', 'public', datetime('now'), datetime('now'))
        """)
        temp_db.conn.commit()

        result = run_async(server._handle_lobster_skill({"action": "list"}))

        assert "skills" in result
        assert result["count"] == 2

    def test_list_filters_by_visibility(self, temp_db):
        """list action should filter by visibility when specified."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        temp_db.cursor.execute("""
            INSERT INTO skills (skill_id, name, owner, visibility, created_at, updated_at)
            VALUES ('skill_pub', 'Public Skill', 'default', 'public', datetime('now'), datetime('now'))
        """)
        temp_db.cursor.execute("""
            INSERT INTO skills (skill_id, name, owner, visibility, created_at, updated_at)
            VALUES ('skill_priv', 'Private Skill', 'default', 'private', datetime('now'), datetime('now'))
        """)
        temp_db.conn.commit()

        result = run_async(
            server._handle_lobster_skill({"action": "list", "visibility": "public"})
        )

        assert "skills" in result
        assert result["count"] == 1
        assert result["skills"][0]["visibility"] == "public"


class TestLobsterSkillInstallAction:
    """Tests for lobster_skill install action."""

    def test_install_returns_error_when_conversation_id_missing(self):
        """install action should return error when conversation_id missing."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()

        result = run_async(server._handle_lobster_skill({"action": "install"}))

        assert "error" in result
        assert "conversation_id is required" in result["error"]

    def test_install_returns_error_when_no_tasks_detected(self, temp_db):
        """install action should return error when no tasks detected."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        with patch("src.skills.task_detector.TaskDetector") as mock_detector_class:
            mock_detector = MagicMock()
            mock_detector.detect_tasks.return_value = []
            mock_detector_class.return_value = mock_detector

            result = run_async(
                server._handle_lobster_skill(
                    {"action": "install", "conversation_id": "conv_no_tasks"}
                )
            )

        assert "error" in result
        assert "No tasks detected" in result["error"]

    def test_install_returns_installed_on_success(self, temp_db):
        """install action should return installed status with skill_id on success."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        with (
            patch("src.skills.task_detector.TaskDetector") as mock_detector_class,
            patch("src.skills.evolver.SkillEvolver") as mock_evolver_class,
        ):
            mock_detector = MagicMock()
            mock_detector.detect_tasks.return_value = [
                {"goal": "Test task creation", "task_id": "task_1"}
            ]
            mock_detector_class.return_value = mock_detector

            mock_evolver = MagicMock()
            mock_evolver.evaluate_and_generate.return_value = "skill_installed_123"
            mock_evolver_class.return_value = mock_evolver

            result = run_async(
                server._handle_lobster_skill(
                    {"action": "install", "conversation_id": "conv_install"}
                )
            )

        assert result["status"] == "installed"
        assert result["skill_id"] == "skill_installed_123"

    def test_install_returns_skipped_when_evaluation_fails(self, temp_db):
        """install action should return skipped when task fails evaluation."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        server._db = temp_db

        with (
            patch("src.skills.task_detector.TaskDetector") as mock_detector_class,
            patch("src.skills.evolver.SkillEvolver") as mock_evolver_class,
        ):
            mock_detector = MagicMock()
            mock_detector.detect_tasks.return_value = [
                {"goal": "Hello there", "task_id": "task_chitchat"}
            ]
            mock_detector_class.return_value = mock_detector

            mock_evolver = MagicMock()
            mock_evolver.evaluate_and_generate.return_value = None
            mock_evolver_class.return_value = mock_evolver

            result = run_async(
                server._handle_lobster_skill(
                    {"action": "install", "conversation_id": "conv_skipped"}
                )
            )

        assert result["status"] == "skipped"
        assert "reason" in result


class TestLobsterSkillUnknownAction:
    """Tests for lobster_skill with unknown action."""

    def test_unknown_action_returns_error(self):
        """Unknown action should return error."""
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()

        result = run_async(server._handle_lobster_skill({"action": "unknown_action"}))

        assert "error" in result
        assert "Unknown action" in result["error"]
