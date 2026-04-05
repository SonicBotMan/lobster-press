#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 4.4 MCP Tools Tests
Tests for lobster_viewer and lobster_import tools
"""

import pytest
import asyncio
import threading
import time
from unittest.mock import Mock, patch, MagicMock


def run_async(coro):
    """Run an async coroutine."""
    return asyncio.run(coro)


class TestPhase4ToolRegistration:
    """Test tool registration"""

    def test_lobster_viewer_registered(self):
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        tool_names = [t.name for t in server.tools]

        assert "lobster_viewer" in tool_names

    def test_lobster_import_registered(self):
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        tool_names = [t.name for t in server.tools]

        assert "lobster_import" in tool_names

    def test_lobster_viewer_schema(self):
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        viewer_tool = next(
            (t for t in server.tools if t.name == "lobster_viewer"), None
        )

        assert viewer_tool is not None
        assert viewer_tool.input_schema["type"] == "object"
        assert "action" in viewer_tool.input_schema["properties"]
        assert "port" in viewer_tool.input_schema["properties"]
        assert "password" in viewer_tool.input_schema["properties"]
        assert viewer_tool.input_schema["properties"]["action"]["enum"] == [
            "start",
            "stop",
            "status",
        ]

    def test_lobster_import_schema(self):
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        server = LobsterPressMCPServer()
        import_tool = next(
            (t for t in server.tools if t.name == "lobster_import"), None
        )

        assert import_tool is not None
        assert import_tool.input_schema["type"] == "object"
        assert "action" in import_tool.input_schema["properties"]
        assert "checkpoint_file" in import_tool.input_schema["properties"]
        assert import_tool.input_schema["properties"]["action"]["enum"] == [
            "scan",
            "start",
            "stop",
        ]
        assert import_tool.input_schema["required"] == ["action"]


class TestHandleLobsterViewer:
    """Test _handle_lobster_viewer"""

    @pytest.fixture
    def server(self):
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        return LobsterPressMCPServer()

    def test_status_not_running(self, server):
        result = run_async(server._handle_lobster_viewer({"action": "status"}))

        assert result["status"] == "stopped"
        assert result["port"] == 18799

    def test_status_running(self, server):
        server._viewer_server = Mock()

        result = run_async(server._handle_lobster_viewer({"action": "status"}))

        assert result["status"] == "running"

    def test_start_launches_server(self, server):
        mock_db = Mock()
        mock_viewer = Mock()
        mock_viewer.serve_forever = Mock()

        with patch(
            "src.viewer.server.start_viewer", return_value=mock_viewer
        ) as mock_start:
            result = run_async(
                server._handle_lobster_viewer({"action": "start", "port": 18799})
            )

        assert result["status"] == "started"
        assert result["port"] == 18799
        assert result["url"] == "http://127.0.0.1:18799"
        mock_start.assert_called_once()

    def test_start_twice_fails(self, server):
        mock_db = Mock()
        mock_viewer = Mock()
        mock_viewer.serve_forever = Mock()
        server._viewer_server = mock_viewer

        with patch("src.viewer.server.start_viewer", return_value=mock_viewer):
            result = run_async(
                server._handle_lobster_viewer({"action": "start", "port": 18799})
            )

        assert result["status"] == "already_running"

    def test_stop_shuts_down(self, server):
        mock_server = Mock()
        server._viewer_server = mock_server

        result = run_async(server._handle_lobster_viewer({"action": "stop"}))

        assert result["status"] == "stopped"
        mock_server.shutdown.assert_called_once()
        assert server._viewer_server is None

    def test_stop_when_not_running(self, server):
        server._viewer_server = None

        result = run_async(server._handle_lobster_viewer({"action": "stop"}))

        assert result["status"] == "not_running"


class TestHandleLobsterImport:
    """Test _handle_lobster_import"""

    @pytest.fixture
    def server(self):
        import sys

        sys.path.insert(0, "mcp_server")
        from lobster_mcp_server import LobsterPressMCPServer

        return LobsterPressMCPServer()

    def test_scan_returns_stats(self, server):
        mock_db = Mock()
        mock_importer = Mock()
        mock_importer.scan = Mock(return_value={"total": 10, "imported": 5})
        server._db = mock_db

        with patch("src.migration.importer.MemoryImporter", return_value=mock_importer):
            result = run_async(server._handle_lobster_import({"action": "scan"}))

        assert result["status"] == "ok"
        assert result["scan"]["total"] == 10

    def test_start_runs_in_background(self, server):
        mock_db = Mock()
        mock_importer = Mock()
        mock_importer.import_memories = Mock()
        server._db = mock_db

        import_called = False

        def capture_import(*args, **kwargs):
            nonlocal import_called
            import_called = True
            return mock_importer

        with patch("src.migration.importer.MemoryImporter", side_effect=capture_import):
            result = run_async(server._handle_lobster_import({"action": "start"}))

        assert result["status"] == "started"

        time.sleep(0.1)
        assert import_called, "MemoryImporter should have been called"

    def test_start_twice_fails(self, server):
        mock_db = Mock()
        mock_importer = Mock()
        server._db = mock_db
        server._importer = mock_importer

        with patch("src.migration.importer.MemoryImporter", return_value=mock_importer):
            result = run_async(server._handle_lobster_import({"action": "start"}))

        assert result["status"] == "already_running"

    def test_stop_marks_importer(self, server):
        mock_importer = Mock()
        server._importer = mock_importer

        result = run_async(server._handle_lobster_import({"action": "stop"}))

        assert result["status"] == "stopped"
        assert server._importer is None

    def test_unknown_action(self, server):
        result = run_async(server._handle_lobster_import({"action": "unknown"}))

        assert "error" in result
        assert "Unknown action" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
