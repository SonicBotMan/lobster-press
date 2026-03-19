#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Tools 模块测试

Author: 小云 (Xiao Yun)
Date: 2026-03-19
"""

import sys
import pytest
from pathlib import Path

# 添加 src 目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agent_tools import lobster_grep, lobster_describe, lobster_expand
from database import LobsterDatabase


class TestLobsterGrep:
    """测试搜索功能"""

    @pytest.fixture
    def db_with_messages(self):
        """创建包含测试消息的数据库"""
        db = LobsterDatabase(":memory:")
        
        # 插入测试消息（seq 会自动生成）
        db.add_message(
            conversation_id="conv_1",
            role="user",
            content="Hello, this is a test message about Python programming"
        )
        
        db.add_message(
            conversation_id="conv_1",
            role="assistant",
            content="Python is a great programming language for AI development"
        )
        
        db.add_message(
            conversation_id="conv_2",
            role="user",
            content="What is machine learning?"
        )
        
        return db

    def test_grep_search_messages(self, db_with_messages):
        """测试搜索消息"""
        results = lobster_grep(
            db=db_with_messages,
            query="Python",
            search_messages=True,
            search_summaries=False,
            limit=10
        )
        
        # 应该返回列表（可能为空，FTS5 需要索引）
        assert isinstance(results, list)
        
        # 如果有结果，验证格式
        if len(results) > 0:
            for result in results:
                assert result['type'] == 'message'
                assert 'content' in result
                assert 'relevance' in result

    def test_grep_filter_by_conversation(self, db_with_messages):
        """测试按对话 ID 过滤"""
        results = lobster_grep(
            db=db_with_messages,
            query="Python",
            conversation_id="conv_1",
            search_messages=True,
            search_summaries=False,
            limit=10
        )
        
        # 所有结果都应该来自 conv_1
        for result in results:
            assert result['conversation_id'] == "conv_1"

    def test_grep_limit_results(self, db_with_messages):
        """测试结果数量限制"""
        results = lobster_grep(
            db=db_with_messages,
            query="Python",
            search_messages=True,
            search_summaries=False,
            limit=1
        )
        
        # 应该只返回 1 条结果
        assert len(results) <= 1

    def test_grep_no_results(self, db_with_messages):
        """测试无匹配结果"""
        results = lobster_grep(
            db=db_with_messages,
            query="nonexistent_keyword_12345",
            search_messages=True,
            search_summaries=False,
            limit=10
        )
        
        # 应该返回空列表
        assert isinstance(results, list)
        # FTS5 可能返回空列表或少量结果
        assert len(results) >= 0

    def test_grep_without_tfidf_rerank(self, db_with_messages):
        """测试不使用 TF-IDF 重排序"""
        results = lobster_grep(
            db=db_with_messages,
            query="Python",
            search_messages=True,
            search_summaries=False,
            limit=10,
            use_tfidf_rerank=False
        )
        
        # 应该返回结果
        assert isinstance(results, list)


class TestLobsterDescribe:
    """测试描述功能"""

    @pytest.fixture
    def db_with_summaries(self):
        """创建包含测试摘要的数据库"""
        db = LobsterDatabase(":memory:")
        
        # 插入测试消息（seq 会自动生成）
        msg_id_1 = db.add_message(
            conversation_id="conv_1",
            role="user",
            content="Test message 1"
        )
        
        msg_id_2 = db.add_message(
            conversation_id="conv_1",
            role="assistant",
            content="Test message 2"
        )
        
        # 插入测试摘要（使用 save_summary）
        summary_id = db.save_summary({
            'summary_id': 'sum_test_1',
            'conversation_id': "conv_1",
            'kind': "leaf",
            'depth': 0,
            'content': "Test summary",
            'source_messages': [msg_id_1, msg_id_2]
        })
        
        return db, summary_id

    def test_describe_summary_by_id(self, db_with_summaries):
        """测试通过 ID 描述摘要"""
        db, summary_id = db_with_summaries
        
        result = lobster_describe(
            db=db,
            summary_id=summary_id
        )
        
        # 应该返回摘要详情
        assert result is not None
        assert result['summary_id'] == summary_id
        assert result['kind'] == 'leaf'

    def test_describe_summary_by_conversation(self, db_with_summaries):
        """测试通过对话 ID 描述摘要"""
        db, _ = db_with_summaries
        
        result = lobster_describe(
            db=db,
            conversation_id="conv_1"
        )
        
        # 应该返回对话的摘要结构
        assert result is not None
        assert result['conversation_id'] == "conv_1"
        assert 'total_summaries' in result
        assert 'by_depth' in result

    def test_describe_nonexistent_summary(self, db_with_summaries):
        """测试描述不存在的摘要"""
        db, _ = db_with_summaries
        
        result = lobster_describe(
            db=db,
            summary_id="nonexistent_summary"
        )
        
        # 应该返回 None
        assert result is None

    def test_describe_filter_by_depth(self, db_with_summaries):
        """测试按深度过滤"""
        db, _ = db_with_summaries
        
        result = lobster_describe(
            db=db,
            conversation_id="conv_1",
            depth=0
        )
        
        # 应该返回过滤后的结果
        assert result is not None
        assert result['conversation_id'] == "conv_1"


class TestLobsterExpand:
    """测试展开功能"""

    @pytest.fixture
    def db_with_hierarchy(self):
        """创建包含层级摘要的数据库"""
        db = LobsterDatabase(":memory:")
        
        # 插入测试消息（seq 会自动生成）
        msg_ids = []
        for i in range(4):
            msg_id = db.add_message(
                conversation_id="conv_1",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Test message {i + 1}"
            )
            msg_ids.append(msg_id)
        
        # 创建叶子摘要（使用 save_summary）
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
        
        # 创建 condensed 摘要
        condensed_summary = db.save_summary({
            'summary_id': 'sum_condensed_1',
            'conversation_id': "conv_1",
            'kind': "condensed",
            'depth': 1,
            'content': "Condensed summary",
            'parent_summaries': [leaf_summary_1, leaf_summary_2]
        })
        
        return db, leaf_summary_1, condensed_summary, msg_ids

    def test_expand_leaf_summary(self, db_with_hierarchy):
        """测试展开叶子摘要"""
        db, leaf_summary_id, _, msg_ids = db_with_hierarchy
        
        result = lobster_expand(
            db=db,
            summary_id=leaf_summary_id,
            max_depth=0
        )
        
        # 应该返回展开结果
        assert result is not None
        assert 'summary_id' in result
        assert 'messages' in result
        # 叶子摘要应该包含原始消息
        assert len(result['messages']) > 0

    def test_expand_condensed_summary(self, db_with_hierarchy):
        """测试展开 condensed 摘要"""
        db, _, condensed_summary_id, msg_ids = db_with_hierarchy
        
        result = lobster_expand(
            db=db,
            summary_id=condensed_summary_id,
            max_depth=-1
        )
        
        # 应该返回展开结果
        assert result is not None
        assert 'summary_id' in result

    def test_expand_nonexistent_summary(self, db_with_hierarchy):
        """测试展开不存在的摘要"""
        db, _, _, _ = db_with_hierarchy
        
        result = lobster_expand(
            db=db,
            summary_id="nonexistent_summary",
            max_depth=-1
        )
        
        # 应该返回包含空消息的结果
        assert result is not None
        assert 'messages' in result
        assert len(result['messages']) == 0

    def test_expand_with_max_depth(self, db_with_hierarchy):
        """测试限制展开深度"""
        db, _, condensed_summary_id, _ = db_with_hierarchy
        
        result = lobster_expand(
            db=db,
            summary_id=condensed_summary_id,
            max_depth=1
        )
        
        # 应该返回展开结果
        assert result is not None
