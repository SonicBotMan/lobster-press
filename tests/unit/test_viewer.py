#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v5.0.0 Viewer Web UI Tests
测试 Memory Viewer HTTP 服务

Author: lobster-press
Date: 2026-04-05
"""

import hashlib
import json
import io
import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from http.server import HTTPServer

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from database import LobsterDatabase
from viewer.server import ViewerHandler, start_viewer


class MockRequest:
    """模拟 HTTP 请求的辅助类"""

    def __init__(self, path="/", headers=None, method="GET"):
        self.path = path
        self._headers = headers or {}
        self.rfile = io.BytesIO(b"")
        self.wfile = io.BytesIO()
        self.requestline = f"{method} {path} HTTP/1.1"
        self.command = method
        self.client_address = ("127.0.0.1", 12345)

    def get(self, name, default=""):
        return self._headers.get(name, default)

    def __getitem__(self, name):
        return self._headers[name]


def make_handler(path="/", headers=None):
    """创建一个 ViewerHandler 实例用于测试"""
    req = MockRequest(path=path, headers=headers)
    handler = ViewerHandler.__new__(ViewerHandler)
    handler.path = path
    handler.headers = req
    handler.rfile = req.rfile
    handler.wfile = req.wfile
    handler.requestline = f"GET {path} HTTP/1.1"
    handler.command = "GET"
    handler.client_address = ("127.0.0.1", 12345)
    handler.server = MagicMock()
    return handler


def get_response(handler):
    """从 handler 的 wfile 中获取响应内容"""
    return handler.wfile.getvalue()


class TestViewerHandlerSetup:
    """测试 ViewerHandler.setup()"""

    def test_setup_sets_db(self):
        db = MagicMock()
        ViewerHandler.setup(db)
        assert ViewerHandler._db is db

    def test_setup_sets_owner(self):
        db = MagicMock()
        ViewerHandler.setup(db, owner="agent:42")
        assert ViewerHandler._session_owner == "agent:42"

    def test_setup_hashes_password(self):
        db = MagicMock()
        ViewerHandler.setup(db, password="secret123")
        expected = hashlib.sha256("secret123".encode()).hexdigest()
        assert ViewerHandler._password_hash == expected

    def test_setup_no_password_sets_none(self):
        db = MagicMock()
        ViewerHandler.setup(db, password=None)
        assert ViewerHandler._password_hash is None

    def test_setup_default_owner(self):
        db = MagicMock()
        ViewerHandler.setup(db)
        assert ViewerHandler._session_owner == "default"


class TestCheckAuth:
    """测试 _check_auth()"""

    def test_returns_true_when_no_password(self):
        ViewerHandler.setup(MagicMock(), password=None)
        handler = make_handler("/")
        assert handler._check_auth() is True

    def test_returns_true_with_valid_cookie(self):
        ViewerHandler.setup(MagicMock(), password="pass")
        handler = make_handler("/", headers={"Cookie": "viewer_auth=authenticated"})
        assert handler._check_auth() is True

    def test_returns_true_with_valid_bearer_token(self):
        pwd = "mypassword"
        ViewerHandler.setup(MagicMock(), password=pwd)
        handler = make_handler("/", headers={"Authorization": f"Bearer {pwd}"})
        assert handler._check_auth() is True

    def test_returns_false_with_invalid_bearer(self):
        ViewerHandler.setup(MagicMock(), password="correct")
        handler = make_handler("/", headers={"Authorization": "Bearer wrong"})
        assert handler._check_auth() is False

    def test_returns_false_when_no_credentials(self):
        ViewerHandler.setup(MagicMock(), password="secret")
        handler = make_handler("/", headers={})
        assert handler._check_auth() is False

    def test_returns_false_when_wrong_cookie(self):
        ViewerHandler.setup(MagicMock(), password="secret")
        handler = make_handler("/", headers={"Cookie": "other=value"})
        assert handler._check_auth() is False


class TestSendJson:
    """测试 _send_json()"""

    def test_sends_json_with_correct_headers(self):
        ViewerHandler.setup(MagicMock())
        handler = make_handler("/")

        with (
            patch.object(handler, "send_response") as mock_status,
            patch.object(handler, "send_header") as mock_header,
            patch.object(handler, "end_headers"),
        ):
            handler._send_json({"key": "value"})

            mock_status.assert_called_once_with(200)
            assert mock_header.call_count >= 2

    def test_encodes_json_correctly(self):
        ViewerHandler.setup(MagicMock())
        handler = make_handler("/")

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._send_json({"msg": "你好世界"})
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert data["msg"] == "你好世界"

    def test_custom_status_code(self):
        ViewerHandler.setup(MagicMock())
        handler = make_handler("/")

        with (
            patch.object(handler, "send_response") as mock_status,
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._send_json({"error": "Not Found"}, 404)
            mock_status.assert_called_once_with(404)


class TestApiMemories:
    """测试 _api_memories()"""

    def test_returns_unauthorized_when_not_authed(self):
        ViewerHandler.setup(MagicMock(), password="secret")
        handler = make_handler("/api/memories", headers={})

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._api_memories()
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert "error" in data

    def test_returns_memories_with_pagination(self):
        mock_db = MagicMock()
        mock_db.get_messages.return_value = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        ViewerHandler.setup(mock_db, password=None)
        handler = make_handler("/api/memories?page=1&limit=10")

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._api_memories()
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert "memories" in data
            assert data["page"] == 1
            assert data["limit"] == 10
            assert data["total"] == 2

    def test_uses_conversation_id_param(self):
        mock_db = MagicMock()
        mock_db.get_messages.return_value = []
        ViewerHandler.setup(mock_db, password=None)
        handler = make_handler("/api/memories?conversation_id=conv_123")

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._api_memories()
            mock_db.get_messages.assert_called_with("conv_123")


class TestApiTasks:
    """测试 _api_tasks()"""

    def test_returns_empty_tasks_list(self):
        ViewerHandler.setup(MagicMock(), password=None)
        handler = make_handler("/api/tasks")

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._api_tasks()
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert data["tasks"] == []
            assert data["count"] == 0

    def test_returns_unauthorized_when_not_authed(self):
        ViewerHandler.setup(MagicMock(), password="secret")
        handler = make_handler("/api/tasks", headers={})

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._api_tasks()
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert "error" in data


class TestApiSkills:
    """测试 _api_skills()"""

    def test_returns_skills_for_owner(self):
        mock_db = MagicMock()
        mock_db.get_skills_by_owner.return_value = [
            {"name": "skill_a", "quality_score": 0.9},
        ]
        ViewerHandler.setup(mock_db, password=None, owner="agent:1")
        handler = make_handler("/api/skills")

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._api_skills()
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert len(data["skills"]) == 1
            assert data["count"] == 1
            mock_db.get_skills_by_owner.assert_called_with(
                "agent:1", include_public=True
            )

    def test_returns_unauthorized_when_not_authed(self):
        ViewerHandler.setup(MagicMock(), password="secret")
        handler = make_handler("/api/skills", headers={})

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._api_skills()
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert "error" in data


class TestApiStats:
    """测试 _api_stats()"""

    def test_returns_stats_object(self):
        mock_db = MagicMock()
        mock_db.cursor = MagicMock()
        mock_db.cursor.fetchone.return_value = (42,)
        ViewerHandler.setup(mock_db, password=None, owner="default")
        handler = make_handler("/api/stats")

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._api_stats()
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert "messages_count" in data
            assert "skills_count" in data
            assert "embeddings_count" in data
            assert "timestamp" in data
            assert data["messages_count"] == 42

    def test_handles_db_errors_gracefully(self):
        mock_db = MagicMock()
        mock_db.cursor = MagicMock()
        mock_db.cursor.execute.side_effect = Exception("DB Error")
        ViewerHandler.setup(mock_db, password=None, owner="default")
        handler = make_handler("/api/stats")

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._api_stats()
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert data["messages_count"] == 0
            assert data["skills_count"] == 0
            assert data["embeddings_count"] == 0

    def test_returns_unauthorized_when_not_authed(self):
        ViewerHandler.setup(MagicMock(), password="secret")
        handler = make_handler("/api/stats", headers={})

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._api_stats()
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert "error" in data


class TestApiConfig:
    """测试 _api_config()"""

    def test_returns_version_and_features(self):
        ViewerHandler.setup(MagicMock(), owner="agent:99")
        handler = make_handler("/api/config")

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._api_config()
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert data["version"] == "5.0.0"
            assert data["owner"] == "agent:99"
            assert data["features"]["memories"] is True
            assert data["features"]["skills"] is True


class TestHealth:
    """测试 _health()"""

    def test_returns_status_ok(self):
        ViewerHandler.setup(MagicMock())
        handler = make_handler("/health")

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._health()
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert data["status"] == "ok"
            assert "timestamp" in data


class TestApiLogin:
    """测试 _api_login()"""

    def test_login_success_with_correct_password(self):
        ViewerHandler.setup(MagicMock(), password="mypass")
        handler = make_handler("/api/login?password=mypass")

        with (
            patch.object(handler, "send_response") as mock_status,
            patch.object(handler, "send_header") as mock_header,
            patch.object(handler, "end_headers"),
        ):
            handler._api_login()
            mock_status.assert_called_once_with(200)
            cookie_calls = [
                call for call in mock_header.call_args_list if "Set-Cookie" in str(call)
            ]
            assert len(cookie_calls) > 0
            cookie_val = str(cookie_calls[0])
            assert "HttpOnly" in cookie_val

    def test_login_failure_with_wrong_password(self):
        ViewerHandler.setup(MagicMock(), password="correct")
        handler = make_handler("/api/login?password=wrong")

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._api_login()
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert "error" in data

    def test_login_failure_when_no_password_set(self):
        ViewerHandler.setup(MagicMock(), password=None)
        handler = make_handler("/api/login?password=anything")

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._api_login()
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert "error" in data


class TestServeIndex:
    """测试 _serve_index()"""

    def test_serves_html_when_authed(self):
        ViewerHandler.setup(MagicMock(), password=None)
        handler = make_handler("/")

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._serve_index()
            raw = get_response(handler)
            html = raw.decode()
            assert "LobsterPress Memory Viewer" in html

    def test_returns_401_when_not_authed(self):
        ViewerHandler.setup(MagicMock(), password="secret")
        handler = make_handler("/", headers={})

        with (
            patch.object(handler, "send_response") as mock_status,
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._serve_index()
            mock_status.assert_called_once_with(401)


class TestDoGET:
    """测试路由 do_GET()"""

    def test_health_route(self):
        ViewerHandler.setup(MagicMock())
        handler = make_handler("/health")

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler.do_GET()
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert data["status"] == "ok"

    def test_config_route(self):
        ViewerHandler.setup(MagicMock())
        handler = make_handler("/api/config")

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler.do_GET()
            raw = get_response(handler)
            data = json.loads(raw.decode())
            assert data["version"] == "5.0.0"


class TestStartViewer:
    """测试 start_viewer()"""

    def test_returns_http_server_instance(self):
        mock_db = MagicMock()
        server = start_viewer(mock_db, port=0)
        assert isinstance(server, HTTPServer)
        server.server_close()

    def test_binds_to_localhost(self):
        mock_db = MagicMock()
        server = start_viewer(mock_db, port=0)
        assert server.server_address[0] == "127.0.0.1"
        server.server_close()

    def test_calls_setup_with_correct_args(self):
        mock_db = MagicMock()
        with patch.object(ViewerHandler, "setup") as mock_setup:
            try:
                server = start_viewer(mock_db, port=0, password="test", owner="agent:x")
                server.server_close()
            except Exception:
                pass
            mock_setup.assert_called_once_with(mock_db, "test", "agent:x")


class TestViewerHtml:
    """测试 HTML 页面内容"""

    def test_html_contains_required_elements(self):
        ViewerHandler.setup(MagicMock())
        handler = make_handler("/")

        with (
            patch.object(handler, "send_response"),
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler._serve_index()
            raw = get_response(handler)
            html = raw.decode()
            assert "🦞" in html
            assert "loadStats" in html
            assert "loadMemories" in html
            assert "/api/stats" in html
            assert "/api/memories" in html
