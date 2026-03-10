#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取式摘要器
基于 RFC #34 的零成本摘要方案

功能：
- 从被丢弃的消息中提取最重要的原句
- 不调用 API，不生成新 token
- 保留原始文字，不引入 AI 幻觉

Author: LobsterPress Team
Version: v1.2.0
"""

import sys
import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ExtractedSummary:
    """提取式摘要结果"""
    summary: str
    char_count: int
    message_count: int
    sources: List[Dict]


class ExtractiveSummarizer:
    """提取式摘要器
    
    从被丢弃的消息中提取最重要的原句：
    - 按重要性排序
    - 限制总字符数
    - 保留原始文字
    """
    
    # 默认最大字符数
    DEFAULT_MAX_CHARS = 200
    
    # 每条消息的最大片段长度
    MAX_SNIPPET_LENGTH = 80
    
    def __init__(self, max_chars: int = 200):
        """初始化摘要器
        
        Args:
            max_chars: 摘要的最大字符数
        """
        self.max_chars = max_chars
    
    def extract_snippet(self, content: str, max_length: int = 80) -> str:
        """从内容中提取片段
        
        Args:
            content: 消息内容
            max_length: 最大长度
        
        Returns:
            提取的片段
        """
        # 移除多余的空白
        content = re.sub(r'\s+', ' ', content).strip()
        
        if len(content) <= max_length:
            return content
        
        # 尝试在句子边界截断
        snippet = content[:max_length]
        
        # 找最后一个句子结束符
        last_sentence_end = max(
            snippet.rfind('。'),
            snippet.rfind('.'),
            snippet.rfind('！'),
            snippet.rfind('!'),
            snippet.rfind('？'),
            snippet.rfind('?'),
        )
        
        if last_sentence_end > max_length * 0.5:
            snippet = snippet[:last_sentence_end + 1]
        else:
            # 没有合适的句子边界，添加省略号
            snippet = snippet.rstrip() + "..."
        
        return snippet
    
    def summarize(self, 
                  dropped_messages: List[Dict],
                  scores: Optional[List[float]] = None) -> ExtractedSummary:
        """生成提取式摘要
        
        Args:
            dropped_messages: 被丢弃的消息列表
            scores: 每条消息的重要性分数（可选）
        
        Returns:
            提取式摘要结果
        """
        if not dropped_messages:
            return ExtractedSummary(
                summary="",
                char_count=0,
                message_count=0,
                sources=[],
            )
        
        # 按重要性排序
        if scores and len(scores) == len(dropped_messages):
            sorted_msgs = sorted(
                zip(dropped_messages, scores),
                key=lambda x: x[1],
                reverse=True
            )
            sorted_msgs = [msg for msg, _ in sorted_msgs]
        else:
            # 没有分数，按原始顺序
            sorted_msgs = dropped_messages
        
        # 提取片段
        parts = []
        total_chars = 0
        sources = []
        
        for msg in sorted_msgs:
            content = msg.get("content", "")
            role = msg.get("role", "unknown")
            
            # 提取片段
            snippet = self.extract_snippet(content, self.MAX_SNIPPET_LENGTH)
            
            # 检查是否超过限制
            part = f"[{role}] {snippet}"
            if total_chars + len(part) > self.max_chars:
                break
            
            parts.append(part)
            total_chars += len(part)
            
            sources.append({
                "role": role,
                "snippet": snippet,
                "original_length": len(content),
            })
        
        # 组合摘要
        if parts:
            summary = "历史摘要: " + " | ".join(parts)
        else:
            summary = ""
        
        return ExtractedSummary(
            summary=summary,
            char_count=len(summary),
            message_count=len(parts),
            sources=sources,
        )
    
    def summarize_to_text(self, 
                          dropped_messages: List[Dict],
                          scores: Optional[List[float]] = None) -> str:
        """生成摘要文本
        
        Args:
            dropped_messages: 被丢弃的消息列表
            scores: 每条消息的重要性分数（可选）
        
        Returns:
            摘要文本
        """
        result = self.summarize(dropped_messages, scores)
        return result.summary


def main():
    """命令行入口"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="提取式摘要器")
    parser.add_argument("input_file", help="输入文件（JSON 格式的消息列表）")
    parser.add_argument("--max-chars", type=int, default=200, help="摘要最大字符数")
    parser.add_argument("--output", help="输出文件")
    
    args = parser.parse_args()
    
    # 读取输入
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 无法读取输入文件: {e}", file=sys.stderr)
        sys.exit(1)
    
    messages = data.get("messages", data) if isinstance(data, dict) else data
    scores = data.get("scores") if isinstance(data, dict) else None
    
    # 生成摘要
    summarizer = ExtractiveSummarizer(max_chars=args.max_chars)
    result = summarizer.summarize(messages, scores)
    
    # 输出
    output = {
        "summary": result.summary,
        "char_count": result.char_count,
        "message_count": result.message_count,
        "sources": result.sources,
    }
    
    output_json = json.dumps(output, indent=2, ensure_ascii=False)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_json)
        print(f"✅ 已写入 {args.output}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
