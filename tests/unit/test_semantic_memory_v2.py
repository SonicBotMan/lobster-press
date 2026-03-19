#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic Memory 模块测试

Author: 小云 (Xiao Yun)
Date: 2026-03-19
"""

import sys
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

# 添加 src 目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic_memory import SemanticMemory
from database import LobsterDatabase


class TestSemanticMemoryInit:
    """测试 SemanticMemory 初始化"""

    def test_init_with_db(self):
        """测试使用数据库初始化"""
        db = LobsterDatabase(":memory:")
        memory = SemanticMemory(db)
        
        assert memory.db == db

    def test_ensure_schema(self):
        """测试创建 schema"""
        db = LobsterDatabase(":memory:")
        memory = SemanticMemory(db)
        
        # 检查 notes 表是否存在
        db.cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='notes'
        """)
        result = db.cursor.fetchone()
        assert result is not None


class TestSaveNote:
    """测试保存笔记"""

    @pytest.fixture
    def memory(self):
        """创建 SemanticMemory 实例"""
        db = LobsterDatabase(":memory:")
        return SemanticMemory(db)

    def test_save_note_basic(self, memory):
        """测试基本保存功能"""
        note_id = memory._save_note(
            conversation_id="conv_1",
            category="preference",
            content="用户偏好使用 PostgreSQL",
            source_msg_ids=["msg_1", "msg_2"]
        )
        
        assert note_id is not None
        assert isinstance(note_id, str)
        assert len(note_id) > 0

    def test_save_note_with_confidence(self, memory):
        """测试带置信度的保存"""
        note_id = memory._save_note(
            conversation_id="conv_1",
            category="fact",
            content="API 版本为 v2.1.0",
            source_msg_ids=["msg_3"],
            confidence=0.9
        )
        
        assert note_id is not None

    def test_save_note_duplicate_skip(self, memory):
        """测试重复内容跳过"""
        # 第一次保存
        note_id_1 = memory._save_note(
            conversation_id="conv_1",
            category="preference",
            content="用户偏好 PostgreSQL",
            source_msg_ids=["msg_1"]
        )
        
        # 第二次保存相同内容（应该返回 None，跳过插入）
        note_id_2 = memory._save_note(
            conversation_id="conv_1",
            category="preference",
            content="用户偏好 PostgreSQL",
            source_msg_ids=["msg_2"]
        )
        
        # 第一次应该成功
        assert note_id_1 is not None
        # 第二次应该返回 None（跳过重复）
        assert note_id_2 is None


class TestGetActiveNotes:
    """测试获取活跃笔记"""

    @pytest.fixture
    def memory_with_notes(self):
        """创建包含笔记的 SemanticMemory"""
        db = LobsterDatabase(":memory:")
        memory = SemanticMemory(db)
        
        # 添加测试笔记
        memory._save_note(
            conversation_id="conv_1",
            category="preference",
            content="用户偏好 PostgreSQL",
            source_msg_ids=["msg_1"]
        )
        
        memory._save_note(
            conversation_id="conv_1",
            category="decision",
            content="项目采用 React 18",
            source_msg_ids=["msg_2"]
        )
        
        memory._save_note(
            conversation_id="conv_2",
            category="fact",
            content="API 版本为 v2.1.0",
            source_msg_ids=["msg_3"]
        )
        
        return memory

    def test_get_active_notes_all(self, memory_with_notes):
        """测试获取所有活跃笔记"""
        notes = memory_with_notes.get_active_notes(conversation_id="conv_1")
        
        assert isinstance(notes, list)
        # 应该有 2 条笔记（conv_1）
        assert len(notes) == 2

    def test_get_active_notes_by_conversation(self, memory_with_notes):
        """测试按对话 ID 获取笔记"""
        notes = memory_with_notes.get_active_notes(conversation_id="conv_1")
        
        assert isinstance(notes, list)
        # 应该有 2 条笔记
        assert len(notes) == 2

    def test_get_active_notes_by_category(self, memory_with_notes):
        """测试按类别获取笔记"""
        notes = memory_with_notes.get_active_notes(
            conversation_id="conv_1",
            categories=["preference"]
        )
        
        assert isinstance(notes, list)
        # 应该有 1 条笔记
        assert len(notes) == 1
        assert notes[0]['category'] == 'preference'

    def test_get_active_notes_empty(self):
        """测试空数据库"""
        db = LobsterDatabase(":memory:")
        memory = SemanticMemory(db)
        
        notes = memory.get_active_notes(conversation_id="conv_1")
        assert notes == []


class TestFormatForContext:
    """测试格式化为上下文"""

    @pytest.fixture
    def memory(self):
        """创建 SemanticMemory 实例"""
        db = LobsterDatabase(":memory:")
        return SemanticMemory(db)

    def test_format_empty_notes(self, memory):
        """测试空笔记列表"""
        result = memory.format_for_context([])
        assert isinstance(result, str)

    def test_format_single_note(self, memory):
        """测试单条笔记"""
        notes = [
            {
                'category': 'preference',
                'content': '用户偏好 PostgreSQL',
                'confidence': 1.0
            }
        ]
        
        result = memory.format_for_context(notes)
        
        assert isinstance(result, str)
        # 输出格式是中文：'用户偏好'
        assert '用户偏好' in result or 'preference' in result
        assert 'PostgreSQL' in result

    def test_format_multiple_notes(self, memory):
        """测试多条笔记"""
        notes = [
            {
                'category': 'preference',
                'content': '用户偏好 PostgreSQL',
                'confidence': 1.0
            },
            {
                'category': 'decision',
                'content': '项目采用 React 18',
                'confidence': 0.9
            }
        ]
        
        result = memory.format_for_context(notes)
        
        assert isinstance(result, str)
        # 输出格式是中文
        assert '用户偏好' in result or 'preference' in result
        assert '技术决策' in result or 'decision' in result
        assert 'PostgreSQL' in result
        assert 'React 18' in result


class TestExtractAndStore:
    """测试提取并存储知识"""

    @pytest.fixture
    def memory(self):
        """创建 SemanticMemory 实例"""
        db = LobsterDatabase(":memory:")
        return SemanticMemory(db)

    def test_extract_and_store_with_mock_llm(self, memory):
        """测试使用 mock LLM 提取知识"""
        # Mock LLM 客户端
        llm_client = Mock()
        llm_client.generate.return_value = json.dumps([
            {
                'category': 'preference',
                'content': '用户偏好 PostgreSQL'
            },
            {
                'category': 'decision',
                'content': '项目采用 React 18'
            }
        ])
        
        messages = [
            {'role': 'user', 'content': '我喜欢 PostgreSQL'},
            {'role': 'assistant', 'content': '好的，我们使用 React 18'}
        ]
        
        note_ids = memory.extract_and_store(
            conversation_id="conv_1",
            messages=messages,
            llm_client=llm_client,
            source_msg_ids=["msg_1", "msg_2"]
        )
        
        # 应该返回 2 个 note_id
        assert isinstance(note_ids, list)
        assert len(note_ids) == 2

    def test_extract_and_store_with_invalid_json(self, memory):
        """测试 LLM 返回无效 JSON"""
        llm_client = Mock()
        llm_client.generate.return_value = "invalid json"
        
        messages = [
            {'role': 'user', 'content': 'Test'}
        ]
        
        note_ids = memory.extract_and_store(
            conversation_id="conv_1",
            messages=messages,
            llm_client=llm_client
        )
        
        # 应该返回空列表（处理错误）
        assert isinstance(note_ids, list)
        assert len(note_ids) == 0

    def test_extract_and_store_with_empty_response(self, memory):
        """测试 LLM 返回空数组"""
        llm_client = Mock()
        llm_client.generate.return_value = "[]"
        
        messages = [
            {'role': 'user', 'content': 'Test'}
        ]
        
        note_ids = memory.extract_and_store(
            conversation_id="conv_1",
            messages=messages,
            llm_client=llm_client
        )
        
        # 应该返回空列表
        assert isinstance(note_ids, list)
        assert len(note_ids) == 0


class TestFormatMessages:
    """测试格式化消息"""

    @pytest.fixture
    def memory(self):
        """创建 SemanticMemory 实例"""
        db = LobsterDatabase(":memory:")
        return SemanticMemory(db)

    def test_format_messages_empty(self, memory):
        """测试空消息列表"""
        result = memory._format_messages([])
        assert isinstance(result, str)

    def test_format_messages_single(self, memory):
        """测试单条消息"""
        messages = [
            {'role': 'user', 'content': 'Hello'}
        ]
        
        result = memory._format_messages(messages)
        
        assert isinstance(result, str)
        assert 'user' in result
        assert 'Hello' in result

    def test_format_messages_multiple(self, memory):
        """测试多条消息"""
        messages = [
            {'role': 'user', 'content': 'Question'},
            {'role': 'assistant', 'content': 'Answer'}
        ]
        
        result = memory._format_messages(messages)
        
        assert isinstance(result, str)
        assert 'Question' in result
        assert 'Answer' in result
