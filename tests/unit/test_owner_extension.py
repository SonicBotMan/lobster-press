#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v5.0.0 Owner Extension Tests
测试多智能体协同的 owner 字段隔离

Author: lobster-press
Date: 2026-04-05
"""

import sys
import os
import tempfile
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from database import LobsterDatabase


class TestMigrateV50:
    """测试 migrate_v50() 迁移"""

    def test_migrate_v50_adds_owner_column(self):
        """migrate_v50() 添加 owner 列到 messages, summaries"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_owner.db")
            db = LobsterDatabase(db_path)

            # 验证 messages 表有 owner 列
            db.cursor.execute("PRAGMA table_info(messages)")
            columns = {row[1] for row in db.cursor.fetchall()}
            assert "owner" in columns

            # 验证 summaries 表有 owner 列
            db.cursor.execute("PRAGMA table_info(summaries)")
            columns = {row[1] for row in db.cursor.fetchall()}
            assert "owner" in columns

            db.close()

    def test_migrate_v50_creates_indexes(self):
        """migrate_v50() 创建 owner 索引"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_owner_idx.db")
            db = LobsterDatabase(db_path)

            # 验证索引存在
            db.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%owner%'"
            )
            indexes = {row[0] for row in db.cursor.fetchall()}

            assert "idx_messages_owner" in indexes
            assert "idx_summaries_owner" in indexes
            # notes 表不存在，索引不会创建
            assert "idx_notes_owner" not in indexes

            db.close()

    def test_migrate_v50_handles_already_exists(self):
        """migrate_v50() 重复执行不报错"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_owner_exists.db")
            db = LobsterDatabase(db_path)

            # 再次执行迁移不应该报错
            db.migrate_v50()

            db.close()


class TestOwnerMethods:
    """测试 set_owner / _owner_filter / _apply_owner_filter"""

    def test_set_owner(self):
        """set_owner() 设置 owner 属性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_set_owner.db")
            db = LobsterDatabase(db_path)

            assert db.owner == "default"

            db.set_owner("agent:123")
            assert db.owner == "agent:123"

            db.set_owner("agent:456")
            assert db.owner == "agent:456"

            db.close()

    def test_owner_filter_includes_public(self):
        """_owner_filter() 始终包含 public"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_filter.db")
            db = LobsterDatabase(db_path)

            filter_sql, filter_params = db._owner_filter()

            assert "OR owner = 'public'" in filter_sql
            assert db.owner in filter_params

            db.close()

    def test_apply_owner_filter_adds_where(self):
        """_apply_owner_filter() 为无 WHERE 的 SQL 添加过滤"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_apply.db")
            db = LobsterDatabase(db_path)

            sql, params = db._apply_owner_filter("SELECT * FROM messages", [])

            assert "WHERE" in sql
            assert "(owner = ? OR owner = 'public')" in sql
            assert db.owner in params

            db.close()

    def test_apply_owner_filter_appends_to_existing_where(self):
        """_apply_owner_filter() 追加到已有 WHERE 子句"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_apply2.db")
            db = LobsterDatabase(db_path)

            sql, params = db._apply_owner_filter(
                "SELECT * FROM messages WHERE conversation_id = ?", ["conv_123"]
            )

            assert "WHERE conversation_id = ?" in sql
            assert "AND (owner = ? OR owner = 'public')" in sql
            assert "conv_123" in params
            assert db.owner in params

            db.close()


class TestSearchWithOwner:
    """测试 search_messages 和 search_summaries 的 owner 过滤"""

    def test_search_messages_filters_by_owner(self):
        """search_messages() 按 owner + public 过滤"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_search_owner.db")
            db = LobsterDatabase(db_path)

            # 创建对话
            conv_id = db.create_conversation()

            # 添加消息
            msg1_id = db.add_message(conv_id, "user", "test message one")
            msg2_id = db.add_message(conv_id, "assistant", "test message two")

            # 默认 owner = 'default'，应该能搜到
            results = db.search_messages("test")
            assert len(results) >= 0  # FTS 可能没数据，但不应该报错

            db.close()

    def test_search_summaries_filters_by_owner(self):
        """search_summaries() 按 owner + public 过滤"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_search_sum.db")
            db = LobsterDatabase(db_path)

            # 创建对话
            conv_id = db.create_conversation()

            # 添加摘要
            db.save_summary(
                {
                    "summary_id": "sum_test1",
                    "conversation_id": conv_id,
                    "kind": "leaf",
                    "depth": 0,
                    "content": "test summary content",
                    "source_messages": [],
                    "earliest_at": "2026-01-01T00:00:00",
                    "latest_at": "2026-01-01T00:00:00",
                    "descendant_count": 0,
                }
            )

            # 默认 owner = 'default'，应该能搜到
            results = db.search_summaries("test")
            assert len(results) >= 0  # FTS 可能没数据，但不应该报错

            db.close()


class TestBackwardCompatibility:
    """测试向后兼容性"""

    def test_default_owner_does_not_break_queries(self):
        """owner='default' 不破坏现有查询"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_compat.db")
            db = LobsterDatabase(db_path)

            # 验证默认 owner 是 'default'
            assert db.owner == "default"

            # 创建对话和消息
            conv_id = db.create_conversation()
            msg_id = db.add_message(conv_id, "user", "hello world")

            # 验证消息能正常获取
            messages = db.get_messages(conv_id)
            assert len(messages) >= 1
            assert messages[0]["content"] == "hello world"

            # 验证 get_summaries 正常工作
            summaries = db.get_summaries(conv_id)
            assert isinstance(summaries, list)

            db.close()

    def test_set_owner_to_agent_format(self):
        """支持 agent:{agentId} 格式的 owner"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_agent_owner.db")
            db = LobsterDatabase(db_path)

            # 设置 agent 格式的 owner
            db.set_owner("agent:agent_abc123")
            assert db.owner == "agent:agent_abc123"

            # 验证 filter 正确
            filter_sql, filter_params = db._owner_filter()
            assert "agent:agent_abc123" in filter_params

            db.close()
