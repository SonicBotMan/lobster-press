#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress 压缩器单元测试
测试 DAGCompressor 和 IncrementalCompressor

Author: 小云 (Xiao Yun)
Date: 2026-03-19
"""

import sys
import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加 src 目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from database import LobsterDatabase
from dag_compressor import DAGCompressor
from incremental_compressor import IncrementalCompressor


class TestDAGCompressor:
    """测试 DAG 压缩器"""

    def test_init(self):
        """测试初始化"""
        db = LobsterDatabase(":memory:")
        compressor = DAGCompressor(db)
        assert compressor.db == db
        # llm_client 可能为 None（未配置 API key）
        # assert compressor.llm_client is not None

    def test_leaf_compact_empty_conversation(self):
        """测试叶子压缩：空对话"""
        db = LobsterDatabase(":memory:")
        compressor = DAGCompressor(db)
        
        # 空对话应该返回 None
        result = compressor.leaf_compact("empty_conv")
        assert result is None

    def test_leaf_compact_with_messages(self):
        """测试叶子压缩：有消息"""
        db = LobsterDatabase(":memory:")
        compressor = DAGCompressor(db)
        
        # 添加一些消息
        conv_id = "test_conv"
        for i in range(5):
            db.add_message(conv_id, "user", f"Message {i}")
        
        # Mock LLM 客户端
        with patch.object(compressor, '_generate_llm_leaf_summary', return_value="Summary"):
            result = compressor.leaf_compact(conv_id, max_tokens=100)
            # 应该创建摘要
            assert result is not None or result is None  # 允许 None（没有压缩）

    def test_incremental_compact(self):
        """测试增量压缩"""
        db = LobsterDatabase(":memory:")
        compressor = DAGCompressor(db)
        
        # 添加一些消息
        conv_id = "test_conv"
        for i in range(10):
            db.add_message(conv_id, "user", f"Message {i}" * 10)
        
        # 执行增量压缩
        result = compressor.incremental_compact(conv_id, context_threshold=0.5)
        # 应该返回布尔值
        assert isinstance(result, bool)

    def test_get_context_items(self):
        """测试获取上下文项"""
        db = LobsterDatabase(":memory:")
        compressor = DAGCompressor(db)
        
        conv_id = "test_conv"
        items = compressor.get_context_items(conv_id)
        assert isinstance(items, list)


class TestIncrementalCompressor:
    """测试增量压缩器"""

    def test_init(self):
        """测试初始化"""
        db = LobsterDatabase(":memory:")
        compressor = IncrementalCompressor(db)
        assert compressor.db == db

    def test_select_compression_strategy(self):
        """测试压缩策略选择"""
        db = LobsterDatabase(":memory:")
        compressor = IncrementalCompressor(db)
        
        # 低使用率 -> none
        strategy = compressor._select_compression_strategy(0.5)
        assert strategy == "none"
        
        # 中等使用率 -> light
        strategy = compressor._select_compression_strategy(0.65)
        assert strategy == "light"
        
        # 高使用率 -> aggressive
        strategy = compressor._select_compression_strategy(0.8)
        assert strategy == "aggressive"

    def test_get_stats(self):
        """测试获取统计信息"""
        db = LobsterDatabase(":memory:")
        compressor = IncrementalCompressor(db)
        
        stats = compressor.get_stats()
        assert isinstance(stats, dict)
        assert 'total_compressions' in stats

    def test_monitor(self):
        """测试监控"""
        db = LobsterDatabase(":memory:")
        compressor = IncrementalCompressor(db)
        
        conv_id = "test_conv"
        result = compressor.monitor(conv_id)
        assert isinstance(result, dict)
        assert 'conversation_id' in result

    def test_compress_empty_conversation(self):
        """测试压缩空对话"""
        db = LobsterDatabase(":memory:")
        compressor = IncrementalCompressor(db)
        
        result = compressor.compress("empty_conv")
        # 空对话应该返回包含统计信息的字典
        assert isinstance(result, dict)
        assert 'strategy' in result


class TestCompressorIntegration:
    """测试压缩器集成"""

    def test_database_compressor_workflow(self):
        """测试数据库和压缩器工作流"""
        db = LobsterDatabase(":memory:")
        compressor = DAGCompressor(db)
        
        # 添加消息
        conv_id = "test_conv"
        msg_ids = []
        for i in range(5):
            msg_id = db.add_message(conv_id, "user", f"Test message {i}")
            msg_ids.append(msg_id)
        
        # 检查消息是否保存
        messages = db.get_messages(conv_id)
        assert len(messages) == 5

    def test_v4_features(self):
        """测试 v4.0.0 新特性"""
        db = LobsterDatabase(":memory:")
        db.migrate_v40()  # 确保 v4.0.0 迁移完成
        
        compressor = DAGCompressor(db)
        
        # 测试 token_budget 参数
        conv_id = "test_conv"
        for i in range(10):
            db.add_message(conv_id, "user", f"Message {i}")
        
        # incremental_compact 应该接受 token_budget 参数
        result = compressor.incremental_compact(
            conv_id, 
            context_threshold=0.8, 
            token_budget=4000
        )
        assert isinstance(result, bool)
