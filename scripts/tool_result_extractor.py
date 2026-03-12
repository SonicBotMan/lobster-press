#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
toolResult 事实提取器 v1.5.0
Issue #76 - toolResult 事实提取

从工具结果中提取关键信息，避免保留冗长的原始内容
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ToolFact:
    """工具事实"""
    key: str
    value: str
    importance: int  # 1-10, 10 最重要


class ToolResultExtractor:
    """工具结果事实提取器
    
    从 toolResult 中提取关键信息，生成简洁的事实摘要
    
    示例输入:
        [Result: Successfully read file /path/to/file.py, 234 lines, 8.5KB]
    
    示例输出:
        [Tool Facts: path=/path/to/file.py; lines=234; size=8.5KB; status=success]
    """
    
    # 文件路径模式
    PATH_PATTERNS = [
        r'(/[a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)',  # Unix 路径
        r'([A-Z]:\\[a-zA-Z0-9_\-\\]+\.[a-zA-Z0-9]+)',  # Windows 路径
        r'(?:path|file|filepath)[:\s]+([^\s,]+)',  # 明确的 path 标记
    ]
    
    # 数字模式（行数、字节数、耗时等）
    NUMBER_PATTERNS = [
        r'(\d+(?:\.\d+)?)\s*lines?',
        r'(\d+(?:\.\d+)?)\s*(?:bytes?|KB|MB|GB)',
        r'(\d+(?:\.\d+)?)\s*(?:seconds?|ms|milliseconds?)',
        r'(\d+(?:\.\d+)?)\s*(?:hits?|matches?|results?)',
        r'found\s+(\d+)',
        r'returned\s+(\d+)',
    ]
    
    # 错误模式
    ERROR_PATTERNS = [
        r'(error|exception|failed|timeout)',
        r'(Error|Exception|Failed|Timeout):\s*([^\n]+)',
    ]
    
    # 成功模式
    SUCCESS_PATTERNS = [
        r'(success|succeeded|completed|done|ok)',
        r'(Successfully|Completed)',
    ]
    
    @classmethod
    def extract_facts(cls, tool_result: str, max_facts: int = 5) -> Tuple[str, List[ToolFact]]:
        """从工具结果中提取事实
        
        Args:
            tool_result: 工具结果文本
            max_facts: 最多提取的事实数量
        
        Returns:
            (事实摘要字符串, 事实列表)
        """
        facts: List[ToolFact] = []
        
        # 1. 提取文件路径
        paths = cls._extract_paths(tool_result)
        for path in paths[:2]:  # 最多 2 个路径
            facts.append(ToolFact(
                key="path",
                value=path,
                importance=8
            ))
        
        # 2. 提取数字结果
        numbers = cls._extract_numbers(tool_result)
        for num_type, num_value in numbers[:3]:  # 最多 3 个数字
            facts.append(ToolFact(
                key=num_type,
                value=num_value,
                importance=6
            ))
        
        # 3. 提取错误信息
        errors = cls._extract_errors(tool_result)
        for error in errors[:1]:  # 最多 1 个错误
            facts.append(ToolFact(
                key="error",
                value=error[:100],  # 限制长度
                importance=9
            ))
        
        # 4. 提取成功/失败状态
        status = cls._extract_status(tool_result)
        facts.append(ToolFact(
            key="status",
            value=status,
            importance=7
        ))
        
        # 按重要性排序，取前 max_facts 个
        facts.sort(key=lambda f: f.importance, reverse=True)
        facts = facts[:max_facts]
        
        # 生成事实摘要
        summary = cls._generate_summary(facts)
        
        return summary, facts
    
    @classmethod
    def _extract_paths(cls, text: str) -> List[str]:
        """提取文件路径"""
        paths = []
        for pattern in cls.PATH_PATTERNS:
            matches = re.findall(pattern, text)
            paths.extend(matches)
        
        # 去重
        seen = set()
        unique_paths = []
        for path in paths:
            if path not in seen:
                seen.add(path)
                unique_paths.append(path)
        
        return unique_paths
    
    @classmethod
    def _extract_numbers(cls, text: str) -> List[Tuple[str, str]]:
        """提取数字结果"""
        numbers = []
        
        for pattern in cls.NUMBER_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # 带单位的情况
                    number = match[0]
                    unit = match[1] if len(match) > 1 else ""
                    numbers.append((unit.lower(), number))
                else:
                    # 纯数字
                    numbers.append(("count", match))
        
        return numbers
    
    @classmethod
    def _extract_errors(cls, text: str) -> List[str]:
        """提取错误信息"""
        errors = []
        
        for pattern in cls.ERROR_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    errors.append(match[-1])  # 取最后一个（错误消息）
                else:
                    errors.append(match)
        
        return errors
    
    @classmethod
    def _extract_status(cls, text: str) -> str:
        """提取成功/失败状态"""
        text_lower = text.lower()
        
        # 先检查错误
        for pattern in cls.ERROR_PATTERNS:
            if re.search(pattern, text_lower):
                return "failure"
        
        # 再检查成功
        for pattern in cls.SUCCESS_PATTERNS:
            if re.search(pattern, text_lower):
                return "success"
        
        return "unknown"
    
    @classmethod
    def _generate_summary(cls, facts: List[ToolFact]) -> str:
        """生成事实摘要"""
        if not facts:
            return "[Tool Facts: none]"
        
        parts = []
        for fact in facts:
            parts.append(f"{fact.key}={fact.value}")
        
        return f"[Tool Facts: {'; '.join(parts)}]"
    
    @classmethod
    def compress_tool_result(cls, tool_result: str, max_length: int = 200) -> str:
        """压缩工具结果
        
        如果结果过长，提取事实；否则保留原文
        
        Args:
            tool_result: 工具结果文本
            max_length: 最大长度阈值
        
        Returns:
            压缩后的文本
        """
        # 如果结果很短，直接返回
        if len(tool_result) <= max_length:
            return tool_result
        
        # 提取事实
        summary, _ = cls.extract_facts(tool_result)
        
        return summary


def main():
    """测试入口"""
    test_results = [
        "[Result: Successfully read file /home/user/project/main.py, 234 lines, 8.5KB]",
        "[Result: Error: File not found at /path/to/missing.txt]",
        "[Result: Search completed, found 15 matches in 3 files, took 0.234 seconds]",
        "[Result: OK]",  # 短结果
        "[Result: " + "x" * 500 + "]",  # 长结果
    ]
    
    print("📊 toolResult 事实提取测试:")
    print("=" * 80)
    
    for i, result in enumerate(test_results, 1):
        print(f"\nTest #{i}:")
        print(f"Input: {result[:80]}...")
        
        summary, facts = ToolResultExtractor.extract_facts(result)
        
        print(f"Summary: {summary}")
        print(f"Facts extracted: {len(facts)}")
        
        for fact in facts:
            print(f"  - {fact.key}: {fact.value} (importance: {fact.importance})")
        
        # 测试压缩
        compressed = ToolResultExtractor.compress_tool_result(result)
        print(f"Compressed: {compressed}")


if __name__ == "__main__":
    main()
