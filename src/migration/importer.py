"""
OpenClaw 原生记忆导入器

借鉴 MemOS 🦐 记忆迁移:
  一键导入 · 智能去重 · 断点续传 · 🦐 标识导入来源

Version: v5.0.0
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime


class MemoryImporter:
    """OpenClaw 原生记忆导入器

    扫描 OpenClaw 原生 SQLite 数据，按 content hash 去重，
    导入时添加 🦐 前缀标识来源。

    Args:
        db: LobsterDatabase 实例
        openclaw_path: OpenClaw 会话目录路径（可选）
    """

    OPENCLAW_DEFAULT_PATH = Path.home() / ".openclaw" / "agents" / "main" / "sessions"

    def __init__(self, db, openclaw_path: str = None):
        self.db = db
        self.openclaw_path = (
            Path(openclaw_path) if openclaw_path else self.OPENCLAW_DEFAULT_PATH
        )
        self._progress = {"stored": 0, "skipped": 0, "merged": 0, "errors": 0}
        self._checkpoint_file = None

    def scan(self) -> Dict:
        """扫描 OpenClaw 原生记忆

        统计可导入的会话文件数和消息数。

        Returns:
            包含 files, sessions, messages 数量的字典
        """
        stats = {
            "files": 0,
            "sessions": 0,
            "messages": 0,
            "errors": 0,
            "scan_path": str(self.openclaw_path),
        }

        if not self.openclaw_path.exists():
            return stats

        for db_path in self.openclaw_path.glob("*.db"):
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                # 检查 messages 表是否存在
                cursor.execute("""
                    SELECT COUNT(*) FROM sqlite_master 
                    WHERE type='table' AND name='messages'
                """)
                if cursor.fetchone()[0] == 0:
                    conn.close()
                    continue

                cursor.execute("SELECT COUNT(*) FROM messages")
                count = cursor.fetchone()[0]

                stats["files"] += 1
                stats["sessions"] += 1
                stats["messages"] += count

                conn.close()
            except Exception as e:
                stats["errors"] += 1
                continue

        return stats

    def import_memories(
        self, on_progress: Callable[[Dict], None] = None, checkpoint_file: str = None
    ) -> Dict:
        """导入记忆（支持断点续传）

        Args:
            on_progress: 进度回调函数 fn(progress_dict)
            checkpoint_file: 断点文件路径（用于续传）

        Returns:
            导入统计字典
        """
        self._reset_progress()
        self._checkpoint_file = checkpoint_file

        # 加载断点
        processed_hashes = self._load_checkpoint()

        if not self.openclaw_path.exists():
            return self._progress

        for db_path in sorted(self.openclaw_path.glob("*.db")):
            try:
                self._import_session_db(db_path, processed_hashes)
            except Exception as e:
                self._progress["errors"] += 1
                print(f"⚠️ Failed to import {db_path.name}: {e}")

            if on_progress:
                on_progress(self._progress.copy())

            # 保存断点
            if checkpoint_file:
                self._save_checkpoint(processed_hashes)

        return self._progress

    def _import_session_db(self, db_path: Path, processed_hashes: set):
        """导入单个会话数据库

        Args:
            db_path: OpenClaw .db 文件路径
            processed_hashes: 已处理的内容 hash 集合
        """
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # 获取消息
            cursor.execute("""
                SELECT message_id, role, content, created_at, metadata
                FROM messages 
                ORDER BY created_at ASC
            """)
            rows = cursor.fetchall()

            for row in rows:
                msg = dict(row)
                content = msg.get("content", "")

                if not content:
                    continue

                # 计算内容 hash
                content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

                if content_hash in processed_hashes:
                    self._progress["skipped"] += 1
                    continue

                # 检查是否已存在
                if self._content_exists(content_hash):
                    processed_hashes.add(content_hash)
                    self._progress["skipped"] += 1
                    continue

                # 导入（添加 🦐 来源标识）
                try:
                    self._import_message(msg, content_hash)
                    processed_hashes.add(content_hash)
                    self._progress["stored"] += 1
                except Exception as e:
                    self._progress["errors"] += 1

        finally:
            conn.close()

    def _content_exists(self, content_hash: str) -> bool:
        """检查内容是否已存在

        Args:
            content_hash: 内容 SHA-256 hash

        Returns:
            True 表示已存在
        """
        self.db.cursor.execute(
            """
            SELECT id FROM messages WHERE metadata LIKE ?
        """,
            (f"%{content_hash}%",),
        )
        return self.db.cursor.fetchone() is not None

    def _import_message(self, msg: Dict, content_hash: str):
        """导入单条消息

        Args:
            msg: 消息字典
            content_hash: 内容 hash
        """
        now = datetime.utcnow().isoformat()

        # 添加元数据
        metadata = json.loads(msg.get("metadata") or "{}")
        metadata["🦐"] = {
            "imported_from": "openclaw",
            "imported_at": now,
            "content_hash": content_hash,
        }

        # 保存到 lobster 数据库
        self.db.save_message(
            {
                "message_id": msg.get("message_id", f"imported_{content_hash}"),
                "conversation_id": msg.get("conversation_id", "imported"),
                "role": msg.get("role", "user"),
                "content": f"🦐 {msg.get('content', '')}",  # 添加 🦐 标识
                "metadata": json.dumps(metadata, ensure_ascii=False),
                "created_at": msg.get("created_at", now),
            }
        )

    def _reset_progress(self):
        """重置进度计数器"""
        self._progress = {"stored": 0, "skipped": 0, "merged": 0, "errors": 0}

    def _load_checkpoint(self) -> set:
        """加载断点

        Returns:
            已处理的内容 hash 集合
        """
        if not self._checkpoint_file:
            return set()

        checkpoint_path = Path(self._checkpoint_file)
        if not checkpoint_path.exists():
            return set()

        try:
            with open(checkpoint_path, "r") as f:
                data = json.load(f)
                return set(data.get("processed_hashes", []))
        except Exception:
            return set()

    def _save_checkpoint(self, processed_hashes: set):
        """保存断点"""
        if not self._checkpoint_file:
            return

        try:
            checkpoint_path = Path(self._checkpoint_file)
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

            with open(checkpoint_path, "w") as f:
                json.dump(
                    {
                        "processed_hashes": list(processed_hashes),
                        "saved_at": datetime.utcnow().isoformat(),
                    },
                    f,
                )
        except Exception as e:
            print(f"⚠️ Failed to save checkpoint: {e}")
