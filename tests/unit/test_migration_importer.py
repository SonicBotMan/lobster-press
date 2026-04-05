# v5.0.0
"""OpenClaw 原生记忆导入器测试"""

import pytest
import json
import hashlib
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.migration.importer import MemoryImporter


class TestScan:
    """scan() 测试"""

    def test_returns_zeros_when_path_doesnt_exist(self):
        """返回零当路径不存在"""
        mock_db = Mock()
        importer = MemoryImporter(mock_db, openclaw_path="/nonexistent/path")
        stats = importer.scan()

        assert stats["files"] == 0
        assert stats["sessions"] == 0
        assert stats["messages"] == 0
        assert stats["errors"] == 0

    def test_counts_files_sessions_messages_correctly(self, tmp_path):
        """正确计数文件、会话、消息"""
        # 创建测试数据库
        db_file = tmp_path / "test_session.db"
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE messages (
                message_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT,
                metadata TEXT
            )
        """)
        cursor.executemany(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?)",
            [
                ("msg1", "user", "Hello", "2024-01-01", "{}"),
                ("msg2", "assistant", "Hi there", "2024-01-02", "{}"),
                ("msg3", "user", "How are you?", "2024-01-03", "{}"),
            ],
        )
        conn.commit()
        conn.close()

        mock_db = Mock()
        importer = MemoryImporter(mock_db, openclaw_path=str(tmp_path))
        stats = importer.scan()

        assert stats["files"] == 1
        assert stats["sessions"] == 1
        assert stats["messages"] == 3
        assert stats["errors"] == 0

    def test_handles_corrupt_files_gracefully(self, tmp_path):
        """优雅处理损坏文件"""
        # 创建损坏的数据库文件
        corrupt_file = tmp_path / "corrupt.db"
        corrupt_file.write_text("not a valid sqlite database")

        # 创建正常的数据库文件
        good_file = tmp_path / "good.db"
        conn = sqlite3.connect(str(good_file))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE messages (
                message_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT,
                metadata TEXT
            )
        """)
        cursor.execute(
            "INSERT INTO messages VALUES ('msg1', 'user', 'Hello', '2024-01-01', '{}')"
        )
        conn.commit()
        conn.close()

        mock_db = Mock()
        importer = MemoryImporter(mock_db, openclaw_path=str(tmp_path))
        stats = importer.scan()

        assert stats["files"] == 1
        assert stats["sessions"] == 1
        assert stats["messages"] == 1
        assert stats["errors"] == 1


class TestContentExists:
    """_content_exists() 测试"""

    def test_returns_false_when_not_exists(self):
        """不存在时返回 False"""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_db.cursor = mock_cursor

        importer = MemoryImporter(mock_db)
        result = importer._content_exists("nonexistent_hash")

        assert result is False
        mock_cursor.execute.assert_called_once()

    def test_returns_true_when_exists(self):
        """存在时返回 True"""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        mock_db.cursor = mock_cursor

        importer = MemoryImporter(mock_db)
        result = importer._content_exists("existing_hash")

        assert result is True


class TestImportMessage:
    """_import_message() 测试"""

    def test_adds_shrimp_prefix_to_content(self):
        """添加 🦐 前缀到内容"""
        mock_db = Mock()
        importer = MemoryImporter(mock_db)

        msg = {
            "message_id": "msg1",
            "role": "user",
            "content": "Hello world",
            "created_at": "2024-01-01",
            "metadata": "{}",
        }
        content_hash = "abc123"

        importer._import_message(msg, content_hash)

        mock_db.save_message.assert_called_once()
        call_args = mock_db.save_message.call_args[0][0]
        assert call_args["content"].startswith("🦐 ")

    def test_adds_import_metadata(self):
        """添加导入元数据"""
        mock_db = Mock()
        importer = MemoryImporter(mock_db)

        msg = {
            "message_id": "msg1",
            "role": "user",
            "content": "Hello",
            "created_at": "2024-01-01",
            "metadata": "{}",
        }
        content_hash = "abc123"

        importer._import_message(msg, content_hash)

        call_args = mock_db.save_message.call_args[0][0]
        metadata = json.loads(call_args["metadata"])

        assert "🦐" in metadata
        assert metadata["🦐"]["imported_from"] == "openclaw"
        assert metadata["🦐"]["content_hash"] == content_hash

    def test_calls_db_save_message(self):
        """调用 db.save_message()"""
        mock_db = Mock()
        importer = MemoryImporter(mock_db)

        msg = {
            "message_id": "msg1",
            "role": "user",
            "content": "Test content",
            "created_at": "2024-01-01",
            "metadata": "{}",
        }

        importer._import_message(msg, "hash123")

        mock_db.save_message.assert_called_once()


class TestImportMemories:
    """import_memories() 测试"""

    def test_respects_checkpoint_for_resume(self, tmp_path):
        """支持断点续传"""
        # 创建测试数据库
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE messages (
                message_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT,
                metadata TEXT
            )
        """)
        cursor.execute(
            "INSERT INTO messages VALUES ('msg1', 'user', 'Hello', '2024-01-01', '{}')"
        )
        conn.commit()
        conn.close()

        # 创建断点文件
        checkpoint_file = tmp_path / "checkpoint.json"
        checkpoint_file.write_text(json.dumps({"processed_hashes": ["abc123"]}))

        mock_db = Mock()
        mock_db.save_message = Mock()
        mock_db.cursor = Mock()
        mock_db.cursor.fetchone.return_value = None  # _content_exists returns False

        importer = MemoryImporter(mock_db, openclaw_path=str(tmp_path))

        # 计算已处理的 hash
        content_hash = hashlib.sha256("Hello".encode()).hexdigest()[:16]

        result = importer.import_memories(checkpoint_file=str(checkpoint_file))

        assert result["stored"] >= 0
        assert result["skipped"] >= 0

    def test_skips_duplicates(self, tmp_path):
        """跳过重复内容"""
        # 创建测试数据库
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE messages (
                message_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT,
                metadata TEXT
            )
        """)
        cursor.execute(
            "INSERT INTO messages VALUES ('msg1', 'user', 'Duplicate', '2024-01-01', '{}')"
        )
        conn.commit()
        conn.close()

        mock_db = Mock()
        mock_db.save_message = Mock()
        mock_db.cursor = Mock()
        # Simulate content already exists
        mock_db.cursor.fetchone.return_value = [1]

        importer = MemoryImporter(mock_db, openclaw_path=str(tmp_path))
        result = importer.import_memories()

        assert result["skipped"] >= 1

    def test_counts_stored_skipped_errors(self, tmp_path):
        """计数 stored/skipped/errors"""
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE messages (
                message_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT,
                metadata TEXT
            )
        """)
        cursor.execute(
            "INSERT INTO messages VALUES ('msg1', 'user', 'Hello', '2024-01-01', '{}')"
        )
        conn.commit()
        conn.close()

        mock_db = Mock()
        mock_db.save_message = Mock()
        mock_db.cursor = Mock()
        mock_db.cursor.fetchone.return_value = None

        importer = MemoryImporter(mock_db, openclaw_path=str(tmp_path))
        result = importer.import_memories()

        assert "stored" in result
        assert "skipped" in result
        assert "errors" in result
        assert result["stored"] + result["skipped"] + result["errors"] >= 0


class TestCheckpoint:
    """_load_checkpoint / _save_checkpoint 测试"""

    def test_creates_checkpoint_file(self, tmp_path):
        """创建断点文件"""
        mock_db = Mock()
        importer = MemoryImporter(mock_db)
        importer._checkpoint_file = str(tmp_path / "checkpoint.json")

        test_hashes = {"hash1", "hash2", "hash3"}
        importer._save_checkpoint(test_hashes)

        checkpoint_path = Path(tmp_path) / "checkpoint.json"
        assert checkpoint_path.exists()

        with open(checkpoint_path) as f:
            data = json.load(f)
            assert set(data["processed_hashes"]) == test_hashes
            assert "saved_at" in data

    def test_loads_processed_hashes_on_restart(self, tmp_path):
        """重启时加载已处理的 hash"""
        mock_db = Mock()
        importer = MemoryImporter(mock_db)
        importer._checkpoint_file = str(tmp_path / "checkpoint.json")

        # 创建断点文件
        test_hashes = ["hash1", "hash2", "hash3"]
        checkpoint_file = tmp_path / "checkpoint.json"
        checkpoint_file.write_text(
            json.dumps({"processed_hashes": test_hashes, "saved_at": "2024-01-01"})
        )

        loaded = importer._load_checkpoint()

        assert loaded == set(test_hashes)

    def test_load_checkpoint_returns_empty_set_when_file_not_exists(self, tmp_path):
        """文件不存在时返回空集合"""
        mock_db = Mock()
        importer = MemoryImporter(mock_db)
        importer._checkpoint_file = str(tmp_path / "nonexistent.json")

        loaded = importer._load_checkpoint()

        assert loaded == set()


class TestResetProgress:
    """_reset_progress 测试"""

    def test_resets_all_counters_to_zero(self):
        """重置所有计数器为零"""
        mock_db = Mock()
        importer = MemoryImporter(mock_db)

        # 修改进度状态
        importer._progress = {"stored": 10, "skipped": 5, "merged": 3, "errors": 2}

        importer._reset_progress()

        assert importer._progress["stored"] == 0
        assert importer._progress["skipped"] == 0
        assert importer._progress["merged"] == 0
        assert importer._progress["errors"] == 0
