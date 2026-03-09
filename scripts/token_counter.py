#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token 精确计数器
使用 tiktoken 进行精确的 Token 计数

Issue: #32 - Token 精确计量
Author: LobsterPress Team
Version: v1.1.1
"""

import sys
import json
import hashlib
from typing import List, Dict, Optional

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    print("⚠️ tiktoken 未安装，使用近似计算", file=sys.stderr)


class TokenCounter:
    """Token 精确计数器"""
    
    # 模型到编码器的映射
    MODEL_ENCODINGS = {
        "gpt-4": "cl100k_base",
        "gpt-4o": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",
        "glm-4": "cl100k_base",  # GLM 使用类似的编码
        "claude-3-opus": "cl100k_base",  # 近似
    }
    
    # 平均每个 Token 的字符数（用于近似计算）
    AVG_CHARS_PER_TOKEN = {
        "en": 4,      # 英文约 4 字符/token
        "zh": 2,      # 中文约 2 字符/token
        "mixed": 3,   # 混合约 3 字符/token
    }
    
    def __init__(self, model: str = "gpt-4o"):
        """初始化 Token 计数器
        
        Args:
            model: 模型名称
        """
        self.model = model
        self.encoding_name = self.MODEL_ENCODINGS.get(model, "cl100k_base")
        
        if TIKTOKEN_AVAILABLE:
            try:
                self.encoder = tiktoken.get_encoding(self.encoding_name)
            except Exception as e:
                print(f"⚠️ 无法加载编码器 {self.encoding_name}: {e}", file=sys.stderr)
                self.encoder = None
        else:
            self.encoder = None
        
        # 缓存
        self._cache: Dict[str, int] = {}
    
    def count_text(self, text: str) -> int:
        """计算文本的 Token 数
        
        Args:
            text: 要计算的文本
        
        Returns:
            Token 数量
        """
        if not text:
            return 0
        
        # 检查缓存
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 精确计算
        if self.encoder:
            count = len(self.encoder.encode(text))
        else:
            # 近似计算
            count = self._approximate_count(text)
        
        # 缓存结果
        self._cache[cache_key] = count
        return count
    
    def count_messages(self, messages: List[Dict]) -> int:
        """计算消息列表的 Token 数
        
        Args:
            messages: 消息列表，格式: [{"role": "user", "content": "..."}]
        
        Returns:
            Token 数量
        """
        total = 0
        
        for msg in messages:
            # 每条消息的基础开销（role + 格式）
            total += 4  # 平均每条消息的格式开销
            
            content = msg.get("content", "")
            if isinstance(content, str):
                total += self.count_text(content)
            elif isinstance(content, list):
                # 多模态消息
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        total += self.count_text(part["text"])
        
        # 对话的基础开销
        total += 3  # priming tokens
        
        return total
    
    def count_file(self, filepath: str) -> int:
        """计算文件的 Token 数
        
        Args:
            filepath: 文件路径
        
        Returns:
            Token 数量
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.count_text(content)
        except Exception as e:
            print(f"❌ 无法读取文件 {filepath}: {e}", file=sys.stderr)
            return 0
    
    def _approximate_count(self, text: str) -> int:
        """近似计算 Token 数
        
        Args:
            text: 要计算的文本
        
        Returns:
            近似 Token 数量
        """
        # 判断语言类型
        zh_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        en_chars = sum(1 for c in text if c.isascii())
        total_chars = len(text)
        
        if total_chars == 0:
            return 0
        
        # 计算中英文比例
        zh_ratio = zh_chars / total_chars if total_chars > 0 else 0
        
        # 根据比例选择系数
        if zh_ratio > 0.7:
            # 中文为主
            chars_per_token = self.AVG_CHARS_PER_TOKEN["zh"]
        elif zh_ratio < 0.3:
            # 英文为主
            chars_per_token = self.AVG_CHARS_PER_TOKEN["en"]
        else:
            # 混合
            chars_per_token = self.AVG_CHARS_PER_TOKEN["mixed"]
        
        return int(total_chars / chars_per_token)
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Token 精确计数器")
    parser.add_argument("input", help="要计算的文本或文件路径")
    parser.add_argument("--model", default="gpt-4o", help="模型名称")
    parser.add_argument("--file", action="store_true", help="输入是文件路径")
    parser.add_argument("--json", action="store_true", help="输入是 JSON 格式的消息列表")
    
    args = parser.parse_args()
    
    counter = TokenCounter(args.model)
    
    if args.file:
        count = counter.count_file(args.input)
    elif args.json:
        try:
            messages = json.loads(args.input)
            count = counter.count_messages(messages)
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        count = counter.count_text(args.input)
    
    print(count)


if __name__ == "__main__":
    main()
