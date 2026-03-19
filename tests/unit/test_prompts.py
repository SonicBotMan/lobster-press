#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prompts 模块测试

Author: 小云 (Xiao Yun)
Date: 2026-03-19
"""

import sys
import pytest
from pathlib import Path

# 添加 src 目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from prompts import (
    build_leaf_summary_prompt,
    build_condensed_summary_prompt,
    build_note_extraction_prompt,
    build_conflict_detection_prompt,
    estimate_tokens,
    truncate_messages,
    LEAF_SUMMARY_PROMPT,
    CONDENSED_SUMMARY_PROMPT,
    NOTE_EXTRACTION_PROMPT,
    CONFLICT_DETECTION_PROMPT
)


class TestPromptConstants:
    """测试 Prompt 常量"""

    def test_leaf_summary_prompt_exists(self):
        """测试叶子摘要 prompt 存在"""
        assert LEAF_SUMMARY_PROMPT is not None
        assert isinstance(LEAF_SUMMARY_PROMPT, str)
        assert len(LEAF_SUMMARY_PROMPT) > 0
        assert "{conversation_text}" in LEAF_SUMMARY_PROMPT

    def test_condensed_summary_prompt_exists(self):
        """测试压缩摘要 prompt 存在"""
        assert CONDENSED_SUMMARY_PROMPT is not None
        assert isinstance(CONDENSED_SUMMARY_PROMPT, str)
        assert len(CONDENSED_SUMMARY_PROMPT) > 0
        assert "{combined_content}" in CONDENSED_SUMMARY_PROMPT
        assert "{depth}" in CONDENSED_SUMMARY_PROMPT

    def test_note_extraction_prompt_exists(self):
        """测试知识提取 prompt 存在"""
        assert NOTE_EXTRACTION_PROMPT is not None
        assert isinstance(NOTE_EXTRACTION_PROMPT, str)
        assert len(NOTE_EXTRACTION_PROMPT) > 0
        # 使用 {context} 而不是 {conversation_text}
        assert "{context}" in NOTE_EXTRACTION_PROMPT

    def test_conflict_detection_prompt_exists(self):
        """测试矛盾检测 prompt 存在"""
        assert CONFLICT_DETECTION_PROMPT is not None
        assert isinstance(CONFLICT_DETECTION_PROMPT, str)
        assert len(CONFLICT_DETECTION_PROMPT) > 0
        assert "{statement1}" in CONFLICT_DETECTION_PROMPT
        assert "{statement2}" in CONFLICT_DETECTION_PROMPT


class TestBuildLeafSummaryPrompt:
    """测试构建叶子摘要 prompt"""

    def test_build_with_empty_messages(self):
        """测试空消息列表"""
        result = build_leaf_summary_prompt([])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_build_with_single_message(self):
        """测试单条消息"""
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        result = build_leaf_summary_prompt(messages)
        assert isinstance(result, str)
        assert "Hello" in result

    def test_build_with_multiple_messages(self):
        """测试多条消息"""
        messages = [
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"},
            {"role": "user", "content": "Question 2"}
        ]
        result = build_leaf_summary_prompt(messages)
        assert isinstance(result, str)
        assert "Question 1" in result
        assert "Answer 1" in result
        assert "Question 2" in result

    def test_build_with_missing_content(self):
        """测试缺少 content 字段"""
        messages = [
            {"role": "user"},  # 缺少 content
            {"role": "assistant", "content": "Answer"}
        ]
        # 应该能处理缺少 content 的情况
        result = build_leaf_summary_prompt(messages)
        assert isinstance(result, str)


class TestBuildCondensedSummaryPrompt:
    """测试构建压缩摘要 prompt"""

    def test_build_with_content_and_depth(self):
        """测试构建压缩摘要 prompt"""
        content = "Summary 1\n\nSummary 2"
        depth = 2
        
        result = build_condensed_summary_prompt(content, depth)
        
        assert isinstance(result, str)
        assert "Summary 1" in result
        assert "Summary 2" in result
        assert "2" in result  # depth

    def test_build_with_empty_content(self):
        """测试空内容"""
        result = build_condensed_summary_prompt("", 1)
        assert isinstance(result, str)

    def test_build_with_different_depths(self):
        """测试不同深度"""
        content = "Test summary"
        
        for depth in [1, 2, 3]:
            result = build_condensed_summary_prompt(content, depth)
            assert str(depth) in result


class TestBuildNoteExtractionPrompt:
    """测试构建知识提取 prompt"""

    def test_build_with_messages(self):
        """测试构建知识提取 prompt"""
        messages = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."}
        ]
        
        result = build_note_extraction_prompt(messages)
        
        assert isinstance(result, str)
        assert "What is Python?" in result
        assert "Python is a programming language." in result

    def test_build_with_empty_messages(self):
        """测试空消息列表"""
        result = build_note_extraction_prompt([])
        assert isinstance(result, str)


class TestBuildConflictDetectionPrompt:
    """测试构建矛盾检测 prompt"""

    def test_build_with_statements(self):
        """测试构建矛盾检测 prompt"""
        statement1 = "Python is slow"
        statement2 = "Python is fast"
        
        result = build_conflict_detection_prompt(statement1, statement2)
        
        assert isinstance(result, str)
        assert statement1 in result
        assert statement2 in result

    def test_build_with_empty_statements(self):
        """测试空陈述"""
        result = build_conflict_detection_prompt("", "")
        assert isinstance(result, str)


class TestEstimateTokens:
    """测试 token 估算"""

    def test_estimate_empty_string(self):
        """测试空字符串"""
        tokens = estimate_tokens("")
        assert tokens == 0

    def test_estimate_short_string(self):
        """测试短字符串"""
        tokens = estimate_tokens("Hello world")
        assert tokens > 0
        # 通常英文约 4 字符 = 1 token
        assert tokens < 10

    def test_estimate_long_string(self):
        """测试长字符串"""
        long_text = "This is a long text. " * 100
        tokens = estimate_tokens(long_text)
        assert tokens > 0
        assert tokens > 100

    def test_estimate_chinese_text(self):
        """测试中文文本"""
        chinese_text = "这是一个中文测试"
        tokens = estimate_tokens(chinese_text)
        assert tokens > 0
        # 中文通常 1-2 字符 = 1 token
        assert tokens > 0


class TestTruncateMessages:
    """测试消息截断"""

    def test_truncate_empty_list(self):
        """测试空列表"""
        result = truncate_messages([])
        assert result == []

    def test_truncate_within_limit(self):
        """测试在限制内"""
        messages = [
            {"role": "user", "content": "Short message"}
        ]
        result = truncate_messages(messages, max_tokens=1000)
        assert len(result) == 1
        assert result[0] == messages[0]

    def test_truncate_exceeds_limit(self):
        """测试超过限制"""
        # 创建超长消息
        long_content = "This is a long message. " * 1000
        messages = [
            {"role": "user", "content": long_content}
        ]
        
        result = truncate_messages(messages, max_tokens=100)
        
        # 应该返回截断后的消息
        assert isinstance(result, list)

    def test_truncate_multiple_messages(self):
        """测试多条消息"""
        messages = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Message 2"},
            {"role": "user", "content": "Message 3"}
        ]
        
        result = truncate_messages(messages, max_tokens=1000)
        
        # 应该保留所有消息（总 token 数小于限制）
        assert len(result) == 3

    def test_truncate_preserves_message_structure(self):
        """测试保留消息结构"""
        messages = [
            {"role": "user", "content": "Test", "timestamp": "2026-03-19"}
        ]
        
        result = truncate_messages(messages, max_tokens=1000)
        
        # 应该保留所有字段
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Test"
        assert "timestamp" in result[0]
