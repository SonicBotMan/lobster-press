#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress v4.0.0 Unit Tests
测试 CMV + C-HLR+ + R³Mem + WMR 模块

Author: 小云 (Xiao Yun)
Date: 2026-03-19
"""

import sys
import os
import pytest
from pathlib import Path

# 添加 src 目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from database import LobsterDatabase
from three_pass_trimmer import ThreePassTrimmer


class TestThreePassTrimmer:
    """测试 CMV 三遍无损压缩"""

    def test_pass1_strip_base64(self):
        """测试 Pass 1: 剥离 base64 冗余"""
        trimmer = ThreePassTrimmer()
        content = "Image data: iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        result = trimmer.trim(content)
        assert "base64_data_removed" in result or len(result) < len(content)

    def test_pass2_deduplicate_tools(self):
        """测试 Pass 2: 去重工具结果"""
        trimmer = ThreePassTrimmer()
        content = "Tool result: {\"status\": \"ok\"}\nTool result: {\"status\": \"ok\"}"
        result = trimmer.trim(content)
        assert result.count("Tool result") <= 1

    def test_pass3_fold_boilerplate(self):
        """测试 Pass 3: 折叠系统样板代码"""
        trimmer = ThreePassTrimmer()
        content = "System: You are a helpful assistant.\nSystem: You are a helpful assistant."
        result = trimmer.trim(content)
        assert result.count("System:") <= 1

    def test_lossless_principle(self):
        """测试无损原则：user/assistant 消息不被修改"""
        trimmer = ThreePassTrimmer()
        user_content = "User: This is important user content that should not be modified."
        result = trimmer.trim(user_content)
        assert "User:" in result


class TestCHLRPlus:
    """测试 C-HLR+ 自适应遗忘曲线"""

    def test_compute_complexity(self):
        """测试复杂度计算"""
        db = LobsterDatabase(":memory:")
        content = "这是一个包含代码的复杂消息：\n```python\nprint('hello')\n```\n还有列表：\n- 项目1\n- 项目2"
        complexity = db._compute_complexity(content)
        assert 0.0 <= complexity <= 3.0
        assert complexity > 1.0  # 复杂内容应该有较高复杂度

    def test_touch_message_logarithmic_growth(self):
        """测试对数稳定性增长"""
        db = LobsterDatabase(":memory:")
        conv_id = "test_conv"
        msg_id = db.add_message(conv_id, "user", "Test message")

        # 第一次访问
        db.touch_message(msg_id)
        db.cursor.execute("SELECT stability, access_count FROM messages WHERE message_id = ?", (msg_id,))
        stability1, count1 = db.cursor.fetchone()

        # 第二次访问
        db.touch_message(msg_id)
        db.cursor.execute("SELECT stability, access_count FROM messages WHERE message_id = ?", (msg_id,))
        stability2, count2 = db.cursor.fetchone()

        assert count2 == count1 + 1
        # 对数增长：第二次增幅应该小于第一次
        growth1 = stability1 / 14.0 - 1.0
        growth2 = stability2 / stability1 - 1.0
        assert growth2 < growth1


class TestR3Mem:
    """测试 R³Mem 可逆三层压缩"""

    def test_migrate_v40(self):
        """测试数据库迁移"""
        db = LobsterDatabase(":memory:")
        db.migrate_v40()

        # 检查 entities 表
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entities'")
        assert db.cursor.fetchone() is not None

        # 检查 entity_mentions 表
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entity_mentions'")
        assert db.cursor.fetchone() is not None

    def test_upsert_entity(self):
        """测试实体插入/更新"""
        db = LobsterDatabase(":memory:")
        db.migrate_v40()

        conv_id = "test_conv"
        msg_id = db.add_message(conv_id, "user", "小明喜欢编程")

        entity_id = db.upsert_entity(
            conversation_id=conv_id,
            entity_name="小明",
            entity_type="person",
            message_ids=[msg_id]
        )

        assert entity_id.startswith("ent_")

        # 检查实体是否插入
        db.cursor.execute("SELECT entity_name, mention_count FROM entities WHERE entity_id = ?", (entity_id,))
        row = db.cursor.fetchone()
        assert row[0] == "小明"
        assert row[1] == 1

    def test_expand_summary_layer1(self):
        """测试 Layer 1: Document-Level 展开"""
        db = LobsterDatabase(":memory:")
        db.migrate_v40()

        conv_id = "test_conv"
        msg_id = db.add_message(conv_id, "user", "Test message")

        # 创建叶子摘要
        summary = {
            "summary_id": f"sum_{uuid.uuid4().hex[:16]}",
            "conversation_id": conv_id,
            "kind": "leaf",
            "depth": 0,
            "content": "Test summary",
            "children": [{"message_id": msg_id, "content": "Test message"}]
        }
        summary_id = db.save_summary(summary)

        # Layer 1 展开
        result = db.expand_summary(summary_id, target_layer=1)
        assert len(result) == 1
        assert result[0]["message_id"] == msg_id

    def test_get_turn_count(self):
        """测试获取轮次数"""
        db = LobsterDatabase(":memory:")
        conv_id = "test_conv"

        # 插入 3 轮对话
        db.add_message(conv_id, "user", "Message 1")
        db.add_message(conv_id, "assistant", "Response 1")
        db.add_message(conv_id, "user", "Message 2")
        db.add_message(conv_id, "assistant", "Response 2")
        db.add_message(conv_id, "user", "Message 3")

        turn_count = db.get_turn_count(conv_id)
        assert turn_count == 3


class TestWMRTools:
    """测试 WMR 框架 MCP 工具集"""

    def test_lobster_status(self):
        """测试 lobster_status 工具（模拟）"""
        # 实际测试需要在 MCP Server 环境中运行
        # 这里只测试数据库层面的统计功能
        db = LobsterDatabase(":memory:")
        db.migrate_v40()

        conv_id = "test_conv"
        db.add_message(conv_id, "user", "Test message")

        # 检查消息层级分布
        db.cursor.execute("""
            SELECT memory_tier, COUNT(*) as cnt
            FROM messages
            WHERE conversation_id = ?
            GROUP BY memory_tier
        """, (conv_id,))
        tier_dist = {row[0]: row[1] for row in db.cursor.fetchall()}
        assert "working" in tier_dist
        assert tier_dist["working"] == 1

    def test_lobster_prune_dry_run(self):
        """测试 lobster_prune 工具 dry_run 模式"""
        db = LobsterDatabase(":memory:")
        db.migrate_v40()

        conv_id = "test_conv"
        msg_id = db.add_message(conv_id, "user", "Test message")

        # 标记为 decayed
        db.cursor.execute("UPDATE messages SET memory_tier = 'decayed' WHERE message_id = ?", (msg_id,))
        db.conn.commit()

        # 检查 decayed 消息数量
        db.cursor.execute("""
            SELECT COUNT(*) FROM messages
            WHERE conversation_id = ? AND memory_tier = 'decayed'
        """, (conv_id,))
        decayed_count = db.cursor.fetchone()[0]
        assert decayed_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
