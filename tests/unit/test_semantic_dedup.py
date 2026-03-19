#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语义去重模块测试

Author: 小云 (Xiao Yun)
Date: 2026-03-19
"""

import sys
import pytest
from pathlib import Path

# 添加 src 目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pipeline.semantic_dedup import SemanticDeduplicator
from pipeline.tfidf_scorer import ScoredMessage


class TestSemanticDeduplicator:
    """测试语义去重器"""

    def test_init(self):
        """测试初始化"""
        dedup = SemanticDeduplicator()
        assert dedup.threshold == 0.82
        assert dedup.min_tokens == 3
        
        # 自定义阈值
        dedup_custom = SemanticDeduplicator(threshold=0.9)
        assert dedup_custom.threshold == 0.9

    def test_tokenize(self):
        """测试分词"""
        dedup = SemanticDeduplicator()
        
        # 简单文本
        tokens = dedup._tokenize("hello world")
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        
        # 空文本
        tokens_empty = dedup._tokenize("")
        assert isinstance(tokens_empty, list)
        
        # 包含标点
        tokens_punct = dedup._tokenize("hello, world!")
        assert isinstance(tokens_punct, list)

    def test_cosine_similarity(self):
        """测试余弦相似度计算"""
        dedup = SemanticDeduplicator()
        
        # 完全相同的文本
        tokens_a = ["hello", "world"]
        tokens_b = ["hello", "world"]
        similarity = dedup._cosine(tokens_a, tokens_b)
        assert 0 <= similarity <= 1
        assert similarity == pytest.approx(1.0, rel=1e-9)  # 允许浮点数误差
        
        # 完全不同的文本
        tokens_c = ["foo", "bar"]
        similarity_diff = dedup._cosine(tokens_a, tokens_c)
        assert 0 <= similarity_diff <= 1
        assert similarity_diff < similarity  # 不同文本相似度更低

    def test_deduplicate_empty_list(self):
        """测试空列表去重"""
        dedup = SemanticDeduplicator()
        
        kept, removed = dedup.deduplicate([])
        assert kept == []
        assert removed == []

    def test_deduplicate_single_message(self):
        """测试单条消息去重"""
        dedup = SemanticDeduplicator()
        
        msg = ScoredMessage(
            id="msg_1",
            role="user",
            content="This is a test message",
            timestamp=1000.0,
            final_score=1.0,
            tokens=["this", "is", "a", "test", "message"]
        )
        
        kept, removed = dedup.deduplicate([msg])
        assert len(kept) == 1
        assert len(removed) == 0
        assert kept[0].id == "msg_1"

    def test_deduplicate_identical_messages(self):
        """测试完全相同的消息去重"""
        dedup = SemanticDeduplicator(threshold=0.8)
        
        msg1 = ScoredMessage(
            id="msg_1",
            role="user",
            content="This is a test message",
            timestamp=1000.0,
            final_score=1.0,
            tokens=["this", "is", "a", "test", "message"]
        )
        
        msg2 = ScoredMessage(
            id="msg_2",
            role="user",
            content="This is a test message",
            timestamp=1001.0,
            final_score=1.0,
            tokens=["this", "is", "a", "test", "message"]
        )
        
        kept, removed = dedup.deduplicate([msg1, msg2])
        # 应该只保留一条
        assert len(kept) == 1
        assert len(removed) == 1
        assert kept[0].id in ["msg_1", "msg_2"]

    def test_deduplicate_different_messages(self):
        """测试不同消息不去重"""
        dedup = SemanticDeduplicator(threshold=0.95)
        
        msg1 = ScoredMessage(
            id="msg_1",
            role="user",
            content="Hello world",
            timestamp=1000.0,
            final_score=1.0,
            tokens=["hello", "world"]
        )
        
        msg2 = ScoredMessage(
            id="msg_2",
            role="user",
            content="Goodbye universe",
            timestamp=1001.0,
            final_score=1.0,
            tokens=["goodbye", "universe"]
        )
        
        kept, removed = dedup.deduplicate([msg1, msg2])
        # 两条消息应该都保留
        assert len(kept) == 2
        assert len(removed) == 0

    def test_deduplicate_with_exempt_message(self):
        """测试豁免消息不被去重"""
        dedup = SemanticDeduplicator(threshold=0.8)
        
        msg1 = ScoredMessage(
            id="msg_1",
            role="user",
            content="This is important",
            timestamp=1000.0,
            final_score=1.0,
            tokens=["this", "is", "important"],
            compression_exempt=True  # 豁免消息
        )
        
        msg2 = ScoredMessage(
            id="msg_2",
            role="user",
            content="Different content",
            timestamp=1001.0,
            final_score=1.0,
            tokens=["different", "content"]
        )
        
        kept, removed = dedup.deduplicate([msg1, msg2])
        # 豁免消息应该保留
        # 不同内容应该都保留
        assert len(kept) == 2
        assert len(removed) == 0
        assert msg1.id in [m.id for m in kept]

    def test_deduplicate_short_messages(self):
        """测试短消息跳过去重"""
        dedup = SemanticDeduplicator()
        
        msg1 = ScoredMessage(
            id="msg_1",
            role="user",
            content="Hi",
            timestamp=1000.0,
            final_score=1.0,
            tokens=["hi"]
        )
        
        msg2 = ScoredMessage(
            id="msg_2",
            role="user",
            content="Hi",
            timestamp=1001.0,
            final_score=1.0,
            tokens=["hi"]
        )
        
        kept, removed = dedup.deduplicate([msg1, msg2])
        # 短消息（<3 tokens）跳过去重
        assert len(kept) == 2
        assert len(removed) == 0

    def test_deduplicate_multiple_duplicates(self):
        """测试多条重复消息去重"""
        dedup = SemanticDeduplicator(threshold=0.8)
        
        messages = [
            ScoredMessage(
                id=f"msg_{i}",
                role="user",
                content="This is a test message",
                timestamp=1000.0 + i,
                final_score=1.0,
                tokens=["this", "is", "a", "test", "message"]
            )
            for i in range(5)
        ]
        
        kept, removed = dedup.deduplicate(messages)
        # 应该只保留一条
        assert len(kept) == 1
        assert len(removed) == 4
