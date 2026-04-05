#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress Memory Viewer

借鉴 MemOS Viewer 架构:
  7 页: memories, tasks, skills, analytics, logs, import, settings
  安全: 仅 127.0.0.1，密码 SHA-256，HttpOnly Cookie

Version: v5.0.0
"""

import hashlib
import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any
from datetime import datetime


class ViewerHandler(BaseHTTPRequestHandler):
    """Viewer HTTP Handler

    提供 7 个页面的 HTTP 服务:
    - GET /: 首页（memories 页面）
    - GET /api/memories: 记忆列表
    - GET /api/tasks: 任务列表
    - GET /api/skills: 技能列表
    - GET /api/stats: 统计信息
    - GET /api/config: 配置信息
    """

    # 类变量存储共享数据
    _db = None
    _password_hash = None
    _session_owner = None

    @classmethod
    def setup(cls, db, password: str = None, owner: str = "default"):
        """初始化处理器类变量

        Args:
            db: LobsterDatabase 实例
            password: 访问密码（SHA-256）
            owner: 当前所有者
        """
        cls._db = db
        cls._session_owner = owner
        if password:
            cls._password_hash = hashlib.sha256(password.encode()).hexdigest()
        else:
            cls._password_hash = None

    def do_GET(self):
        """处理 GET 请求"""
        path = urlparse(self.path).path

        # 路由
        if path == "/" or path == "/index.html":
            self._serve_index()
        elif path == "/api/memories":
            self._api_memories()
        elif path == "/api/tasks":
            self._api_tasks()
        elif path == "/api/skills":
            self._api_skills()
        elif path == "/api/stats":
            self._api_stats()
        elif path == "/api/config":
            self._api_config()
        elif path == "/api/login":
            self._api_login()
        elif path == "/health":
            self._health()
        else:
            self.send_error(404)

    def _check_auth(self) -> bool:
        """检查认证状态"""
        if not self._password_hash:
            return True

        # 检查 Cookie
        cookie = self.headers.get("Cookie", "")
        if "viewer_auth=" in cookie:
            return True

        # 检查 Authorization header
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            if hashlib.sha256(token.encode()).hexdigest() == self._password_hash:
                return True

        return False

    def _send_json(self, data: Dict, status: int = 200):
        """发送 JSON 响应"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _serve_index(self):
        """服务 HTML 页面"""
        if not self._check_auth():
            self.send_response(401)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body>"
                b"<h1>401 Unauthorized</h1>"
                b"<p>Please login first.</p>"
                b"</body></html>"
            )
            return

        html = self._get_viewer_html()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def _api_memories(self):
        """记忆列表 API"""
        if not self._check_auth():
            self._send_json({"error": "Unauthorized"}, 401)
            return

        params = parse_qs(urlparse(self.path).query)
        page = int(params.get("page", ["1"])[0])
        limit = int(params.get("limit", ["20"])[0])
        conversation_id = params.get("conversation_id", [None])[0]

        offset = (page - 1) * limit

        # 获取记忆
        db = self._get_db()
        db.set_owner(self._session_owner)

        if conversation_id:
            messages = db.get_messages(conversation_id)
        else:
            messages = db.get_messages("default")[:limit]  # 简化

        self._send_json(
            {
                "memories": messages[offset : offset + limit],
                "page": page,
                "limit": limit,
                "total": len(messages),
            }
        )

    def _api_tasks(self):
        """任务列表 API"""
        if not self._check_auth():
            self._send_json({"error": "Unauthorized"}, 401)
            return

        # 简化实现：返回空列表或从数据库读取
        self._send_json({"tasks": [], "count": 0})

    def _api_skills(self):
        """技能列表 API"""
        if not self._check_auth():
            self._send_json({"error": "Unauthorized"}, 401)
            return

        db = self._get_db()
        db.set_owner(self._session_owner)

        skills = db.get_skills_by_owner(self._session_owner, include_public=True)

        self._send_json({"skills": skills, "count": len(skills)})

    def _api_stats(self):
        """统计信息 API"""
        if not self._check_auth():
            self._send_json({"error": "Unauthorized"}, 401)
            return

        db = self._get_db()
        db.set_owner(self._session_owner)

        stats = {
            "messages_count": 0,
            "summaries_count": 0,
            "skills_count": 0,
            "embeddings_count": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 统计消息数
        try:
            db.cursor.execute(
                "SELECT COUNT(*) FROM messages WHERE owner = ? OR owner = 'public'",
                (self._session_owner,),
            )
            stats["messages_count"] = db.cursor.fetchone()[0]
        except Exception:
            pass

        # 统计技能数
        try:
            db.cursor.execute(
                "SELECT COUNT(*) FROM skills WHERE owner = ? OR visibility = 'public'",
                (self._session_owner,),
            )
            stats["skills_count"] = db.cursor.fetchone()[0]
        except Exception:
            pass

        # 统计嵌入数
        try:
            db.cursor.execute("SELECT COUNT(*) FROM embeddings")
            stats["embeddings_count"] = db.cursor.fetchone()[0]
        except Exception:
            pass

        self._send_json(stats)

    def _api_config(self):
        """配置信息 API"""
        self._send_json(
            {
                "version": "5.0.0",
                "owner": self._session_owner,
                "features": {
                    "memories": True,
                    "tasks": True,
                    "skills": True,
                    "analytics": True,
                    "import": True,
                },
            }
        )

    def _api_login(self):
        """登录 API"""
        params = parse_qs(urlparse(self.path).query)
        password = params.get("password", [""])[0]

        if (
            self._password_hash
            and hashlib.sha256(password.encode()).hexdigest() == self._password_hash
        ):
            self.send_response(200)
            self.send_header(
                "Set-Cookie",
                "viewer_auth=authenticated; HttpOnly; Path=/; Max-Age=3600",
            )
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self._send_json({"error": "Invalid password"}, 401)

    def _health(self):
        """健康检查"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(
            json.dumps(
                {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
            ).encode()
        )

    def _get_db(self):
        """获取数据库实例"""
        return self._db

    def _get_viewer_html(self) -> str:
        """生成 Viewer HTML 页面"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LobsterPress Memory Viewer</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }
        h1 { color: #ff6b6b; }
        .nav { margin: 20px 0; }
        .nav a { color: #4ecdc4; margin-right: 15px; text-decoration: none; }
        .nav a:hover { text-decoration: underline; }
        .card { background: #16213e; border-radius: 8px; padding: 15px; margin: 10px 0; }
        .card h3 { color: #4ecdc4; margin-top: 0; }
        .stats { display: flex; gap: 15px; flex-wrap: wrap; }
        .stat { background: #0f3460; padding: 10px 15px; border-radius: 5px; }
        .stat-value { font-size: 24px; font-weight: bold; color: #ff6b6b; }
        .stat-label { font-size: 12px; color: #888; }
        pre { background: #0f3460; padding: 10px; border-radius: 5px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>🦞 LobsterPress Memory Viewer</h1>
    <div class="nav">
        <a href="/">Memories</a>
        <a href="/api/tasks">Tasks</a>
        <a href="/api/skills">Skills</a>
        <a href="/api/stats">Analytics</a>
    </div>
    <div class="stats" id="stats"></div>
    <div id="content">Loading...</div>
    <script>
        async function loadStats() {
            const r = await fetch('/api/stats');
            const d = await r.json();
            document.getElementById('stats').innerHTML = `
                <div class="stat"><div class="stat-value">${d.messages_count}</div><div class="stat-label">Messages</div></div>
                <div class="stat"><div class="stat-value">${d.skills_count}</div><div class="stat-label">Skills</div></div>
                <div class="stat"><div class="stat-value">${d.embeddings_count}</div><div class="stat-label">Embeddings</div></div>
            `;
        }
        async function loadMemories() {
            const r = await fetch('/api/memories?limit=10');
            const d = await r.json();
            document.getElementById('content').innerHTML = d.memories.map(m => `
                <div class="card">
                    <h3>${m.role || 'unknown'}</h3>
                    <p>${(m.content || '').substring(0, 200)}...</p>
                    <small>${m.created_at || ''}</small>
                </div>
            `).join('');
        }
        loadStats();
        loadMemories();
    </script>
</body>
</html>"""

    def log_message(self, format, *args):
        """覆盖日志输出，避免污染 stderr"""
        pass


def start_viewer(
    db, port: int = 18799, password: str = None, owner: str = "default"
) -> HTTPServer:
    """启动 Viewer HTTP 服务

    Args:
        db: LobsterDatabase 实例
        port: 监听端口（默认 18799）
        password: 访问密码（可选）
        owner: 当前所有者

    Returns:
        HTTPServer 实例
    """
    ViewerHandler.setup(db, password, owner)

    server = HTTPServer(("127.0.0.1", port), ViewerHandler)
    print(f"🦞 LobsterPress Viewer: http://127.0.0.1:{port}")
    print(f"   Owner: {owner}")
    if password:
        print(f"   Password: {'*' * len(password)}")
    else:
        print(f"   Password: None (no auth)")

    return server
