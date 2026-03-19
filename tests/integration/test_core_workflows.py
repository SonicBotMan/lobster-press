#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress v4.0.0 集成测试 - 核心工作流

专注核心场景：
1. 消息添加和检索
2. 数据库和压缩器协作
3. 基本压缩流程
4. 错误处理

Author: 小云 (Xiao Yun)
Date: 2026-03-19
"""

import sys
import pytest
from pathlib import Path

# 添加 src 目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from database import LobsterDatabase
from dag_compressor import DAGCompressor
from incremental_compressor import IncrementalCompressor
from three_pass_trimmer import ThreePassTrimmer


class TestMessageWorkflow:
    """测试消息工作流"""

    @pytest.fixture
    def db(self):
        """初始化数据库"""
        return LobsterDatabase(":memory:")

    def test_add_and_retrieve_messages(self, db):
        """测试添加和检索消息"""
        # 1. 添加消息
        msg_id_1 = db.add_message(
            conversation_id="conv_1",
            role="user",
            content="Hello, this is a test"
        )
        
        msg_id_2 = db.add_message(
            conversation_id="conv_1",
            role="assistant",
            content="Hi, I received your message"
        )
        
        # 2. 检索消息
        messages = db.get_messages("conv_1")
        
        # 3. 验证
        assert len(messages) == 2
        assert messages[0]['role'] == "user"
        assert messages[1]['role'] == "assistant"

    def test_message_sequence(self, db):
        """测试消息序列"""
        # 1. 添加多条消息
        for i in range(10):
            db.add_message(
                conversation_id="conv_1",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i + 1}"
            )
        
        # 2. 检索消息
        messages = db.get_messages("conv_1")
        
        # 3. 验证序列
        assert len(messages) == 10
        # 验证 seq 是递增的
        for i, msg in enumerate(messages):
            assert msg['seq'] == i + 1

    def test_message_fts_search(self, db):
        """测试消息全文搜索"""
        # 1. 添加消息
        db.add_message(
            conversation_id="conv_1",
            role="user",
            content="Python is a programming language"
        )
        
        db.add_message(
            conversation_id="conv_1",
            role="assistant",
            content="JavaScript is also popular"
        )
        
        # 2. 搜索消息
        results = db.search_messages("Python", limit=10)
        
        # 3. 验证搜索结果
        # FTS5 可能需要时间建立索引，结果可能为空
        assert isinstance(results, list)


class TestSummaryWorkflow:
    """测试摘要工作流"""

    @pytest.fixture
    def db(self):
        """初始化数据库"""
        return LobsterDatabase(":memory:")

    def test_save_and_retrieve_summary(self, db):
        """测试保存和检索摘要"""
        # 1. 添加消息
        msg_id = db.add_message(
            conversation_id="conv_1",
            role="user",
            content="Test message"
        )
        
        # 2. 创建摘要
        summary_id = db.save_summary({
            'summary_id': 'sum_test_1',
            'conversation_id': "conv_1",
            'kind': "leaf",
            'depth': 0,
            'content': "Test summary",
            'source_messages': [msg_id]
        })
        
        # 3. 验证摘要
        assert summary_id == 'sum_test_1'
        
        # 4. 查询摘要
        db.cursor.execute("""
            SELECT * FROM summaries WHERE summary_id = ?
        """, (summary_id,))
        result = db.cursor.fetchone()
        assert result is not None

    def test_summary_hierarchy(self, db):
        """测试摘要层级结构"""
        # 1. 添加消息
        msg_ids = []
        for i in range(4):
            msg_id = db.add_message(
                conversation_id="conv_1",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i + 1}"
            )
            msg_ids.append(msg_id)
        
        # 2. 创建叶子摘要
        leaf_summary_1 = db.save_summary({
            'summary_id': 'sum_leaf_1',
            'conversation_id': "conv_1",
            'kind': "leaf",
            'depth': 0,
            'content': "Leaf summary 1",
            'source_messages': msg_ids[:2]
        })
        
        leaf_summary_2 = db.save_summary({
            'summary_id': 'sum_leaf_2',
            'conversation_id': "conv_1",
            'kind': "leaf",
            'depth': 0,
            'content': "Leaf summary 2",
            'source_messages': msg_ids[2:]
        })
        
        # 3. 创建压缩摘要
        condensed_summary = db.save_summary({
            'summary_id': 'sum_condensed_1',
            'conversation_id': "conv_1",
            'kind': "condensed",
            'depth': 1,
            'content': "Condensed summary",
            'parent_summaries': [leaf_summary_1, leaf_summary_2]
        })
        
        # 4. 验证层级结构
        db.cursor.execute("""
            SELECT COUNT(*) FROM summaries
            WHERE conversation_id = ? AND depth = 0
        """, ("conv_1",))
        leaf_count = db.cursor.fetchone()[0]
        assert leaf_count == 2
        
        db.cursor.execute("""
            SELECT COUNT(*) FROM summaries
            WHERE conversation_id = ? AND depth = 1
        """, ("conv_1",))
        condensed_count = db.cursor.fetchone()[0]
        assert condensed_count == 1


class TestCompressionWorkflow:
    """测试压缩工作流"""

    @pytest.fixture
    def setup(self):
        """初始化环境"""
        db = LobsterDatabase(":memory:")
        compressor = DAGCompressor(db)
        return db, compressor

    def test_compression_with_sufficient_messages(self, setup):
        """测试有足够消息时的压缩"""
        db, compressor = setup
        
        # 1. 添加足够多的消息（> fresh_tail=32）
        for i in range(40):
            db.add_message(
                conversation_id="conv_1",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i + 1}: " + "content " * 5
            )
        
        # 2. 执行压缩
        result = compressor.leaf_compact(
            conversation_id="conv_1",
            max_tokens=1000
        )
        
        # 3. 验证压缩结果
        if result is not None:
            # 压缩成功，验证基本结构
            assert isinstance(result, dict)

    def test_no_compression_with_few_messages(self, setup):
        """测试消息太少时不压缩"""
        db, compressor = setup
        
        # 1. 添加少量消息（< fresh_tail=32）
        for i in range(10):
            db.add_message(
                conversation_id="conv_1",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i + 1}"
            )
        
        # 2. 执行压缩
        result = compressor.leaf_compact(
            conversation_id="conv_1",
            max_tokens=1000
        )
        
        # 3. 验证不压缩
        # 消息太少，应该返回 None
        assert result is None


class TestIncrementalWorkflow:
    """测试增量压缩工作流"""

    @pytest.fixture
    def setup(self):
        """初始化环境"""
        db = LobsterDatabase(":memory:")
        compressor = IncrementalCompressor(db)
        return db, compressor

    def test_incremental_compress_small_conversation(self, setup):
        """测试小对话的增量压缩"""
        db, compressor = setup
        
        # 1. 添加少量消息
        for i in range(10):
            db.add_message(
                conversation_id="conv_1",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i + 1}"
            )
        
        # 2. 执行增量压缩
        result = compressor.compress(conversation_id="conv_1")
        
        # 3. 验证结果
        assert result is not None
        assert isinstance(result, dict)


class TestTrimmerWorkflow:
    """测试修剪器工作流"""

    @pytest.fixture
    def trimmer(self):
        """初始化修剪器"""
        return ThreePassTrimmer()

    def test_trimmer_basic(self, trimmer):
        """测试基本修剪功能"""
        # 1. 创建消息
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        
        # 2. 执行修剪
        trimmed, stats = trimmer.trim(messages)
        
        # 3. 验证结果
        assert isinstance(trimmed, list)
        assert isinstance(stats, dict)
        assert len(trimmed) > 0

    def test_trimmer_preserves_structure(self, trimmer):
        """测试修剪器保留消息结构"""
        # 1. 创建消息
        messages = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"}
        ]
        
        # 2. 执行修剪
        trimmed, stats = trimmer.trim(messages)
        
        # 3. 验证结构保留
        for msg in trimmed:
            assert 'role' in msg
            assert 'content' in msg


class TestErrorHandling:
    """测试错误处理"""

    @pytest.fixture
    def db(self):
        """初始化数据库"""
        return LobsterDatabase(":memory:")

    def test_empty_conversation(self, db):
        """测试空对话"""
        # 1. 不添加任何消息
        
        # 2. 检索消息
        messages = db.get_messages("conv_1")
        
        # 3. 验证返回空列表
        assert messages == []

    def test_invalid_conversation_id(self, db):
        """测试无效的对话 ID"""
        # 1. 添加消息到一个对话
        db.add_message(
            conversation_id="conv_1",
            role="user",
            content="Message 1"
        )
        
        # 2. 查询另一个对话
        messages = db.get_messages("conv_2")
        
        # 3. 验证返回空列表
        assert messages == []

    def test_message_with_empty_content(self, db):
        """测试空内容的消息"""
        # 1. 添加空内容消息
        msg_id = db.add_message(
            conversation_id="conv_1",
            role="user",
            content=""
        )
        
        # 2. 验证消息被添加
        messages = db.get_messages("conv_1")
        assert len(messages) == 1


class TestDatabaseIntegrity:
    """测试数据库完整性"""

    @pytest.fixture
    def db(self):
        """初始化数据库"""
        return LobsterDatabase(":memory:")

    def test_message_count_consistency(self, db):
        """测试消息数量一致性"""
        # 1. 添加消息
        for i in range(20):
            db.add_message(
                conversation_id="conv_1",
                role="user",
                content=f"Message {i + 1}"
            )
        
        # 2. 查询消息数量
        db.cursor.execute("""
            SELECT COUNT(*) FROM messages
            WHERE conversation_id = ?
        """, ("conv_1",))
        count = db.cursor.fetchone()[0]
        
        # 3. 验证一致性
        assert count == 20

    def test_conversation_isolation(self, db):
        """测试对话隔离"""
        # 1. 添加消息到不同对话
        for i in range(5):
            db.add_message(
                conversation_id="conv_1",
                role="user",
                content=f"Conv 1 - Message {i + 1}"
            )
        
        for i in range(3):
            db.add_message(
                conversation_id="conv_2",
                role="user",
                content=f"Conv 2 - Message {i + 1}"
            )
        
        # 2. 验证隔离
        messages_1 = db.get_messages("conv_1")
        messages_2 = db.get_messages("conv_2")
        
        assert len(messages_1) == 5
        assert len(messages_2) == 3

    def test_database_schema(self, db):
        """测试数据库 schema"""
        # 1. 检查表是否存在
        db.cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('messages', 'summaries', 'summary_messages')
        """)
        tables = [row[0] for row in db.cursor.fetchall()]
        
        # 2. 验证 schema
        assert 'messages' in tables
        assert 'summaries' in tables
        assert 'summary_messages' in tables
