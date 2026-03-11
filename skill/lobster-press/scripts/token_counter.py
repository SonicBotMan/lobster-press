#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token 计数器 v1.2.0
支持多语言/多模型的 Token 计数

Issue: #40 - 多语言/多模型 Token 计数优化
Author: LobsterPress Team
Version: v1.3.0
"""

import sys
import json
import re
import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class TokenCountResult:
    """Token 计数结果"""
    count: int
    model: str
    method: str  # "exact" or "approximate"
    confidence: float  # 0.0-1.0


class BaseTokenCounter(ABC):
    """Token 计数器基类"""
    
    @abstractmethod
    def count(self, text: str) -> TokenCountResult:
        """计算 Token 数
        
        Args:
            text: 要计算的文本
        
        Returns:
            TokenCountResult
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查计数器是否可用
        
        Returns:
            是否可用
        """
        pass


class TiktokenCounter(BaseTokenCounter):
    """tiktoken 计数器（OpenAI 模型）"""
    
    def __init__(self, encoding: str = "cl100k_base"):
        self.encoding_name = encoding
        self.encoder = None
        
        try:
            import tiktoken
            self.encoder = tiktoken.get_encoding(encoding)
        except ImportError:
            pass
    
    def is_available(self) -> bool:
        return self.encoder is not None
    
    def count(self, text: str) -> TokenCountResult:
        if not self.is_available():
            raise RuntimeError("tiktoken 不可用")
        
        count = len(self.encoder.encode(text))
        return TokenCountResult(
            count=count,
            model=f"tiktoken:{self.encoding_name}",
            method="exact",
            confidence=0.95
        )


class GLMTokenCounter(BaseTokenCounter):
    """GLM Token 计数器（智谱模型）
    
    使用改进的中英文混合估计算法
    """
    
    # GLM 模型的 Token 估算参数
    # 基于 GLM-4 的实际测试数据
    GLM_PARAMS = {
        "zh_avg_chars": 1.8,    # 中文平均 1.8 字符/token
        "en_avg_chars": 4.0,    # 英文平均 4.0 字符/token
        "code_avg_chars": 3.5,  # 代码平均 3.5 字符/token
    }
    
    def __init__(self, model: str = "glm-4"):
        self.model = model
    
    def is_available(self) -> bool:
        return True  # 总是可用（基于估算）
    
    def count(self, text: str) -> TokenCountResult:
        if not text:
            return TokenCountResult(count=0, model=self.model, method="approximate", confidence=0.85)
        
        # 分析文本组成
        zh_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        en_chars = sum(1 for c in text if c.isascii() and c.isalnum())
        code_chars = self._count_code_chars(text)
        other_chars = len(text) - zh_chars - en_chars - code_chars
        
        total_chars = len(text)
        if total_chars == 0:
            return TokenCountResult(count=0, model=self.model, method="approximate", confidence=0.85)
        
        # 计算各部分的 token 数
        zh_tokens = zh_chars / self.GLM_PARAMS["zh_avg_chars"]
        en_tokens = en_chars / self.GLM_PARAMS["en_avg_chars"]
        code_tokens = code_chars / self.GLM_PARAMS["code_avg_chars"]
        other_tokens = other_chars / 4.0  # 其他字符默认按英文计算
        
        total_tokens = int(zh_tokens + en_tokens + code_tokens + other_tokens)
        
        return TokenCountResult(
            count=total_tokens,
            model=self.model,
            method="approximate",
            confidence=0.85
        )
    
    def _count_code_chars(self, text: str) -> int:
        """计算代码字符数"""
        # 简单识别代码：包含特定符号和关键字
        code_patterns = [
            r'```[\s\S]*?```',  # 代码块
            r'`[^`]+`',          # 行内代码
            r'\{[\s\S]*?\}',     # 大括号内容
            r'def |class |function |import |from ',  # 关键字
        ]
        
        count = 0
        for pattern in code_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                count += len(match)
        
        return count


class QwenTokenCounter(BaseTokenCounter):
    """Qwen Token 计数器（阿里模型）
    
    Qwen 对中文支持更好，token 效率更高
    """
    
    # Qwen 模型的 Token 估算参数
    QWEN_PARAMS = {
        "zh_avg_chars": 1.5,    # Qwen 中文更高效
        "en_avg_chars": 4.0,
        "code_avg_chars": 3.2,
    }
    
    def __init__(self, model: str = "qwen"):
        self.model = model
    
    def is_available(self) -> bool:
        return True
    
    def count(self, text: str) -> TokenCountResult:
        if not text:
            return TokenCountResult(count=0, model=self.model, method="approximate", confidence=0.85)
        
        # 分析文本组成
        zh_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        en_chars = sum(1 for c in text if c.isascii() and c.isalnum())
        other_chars = len(text) - zh_chars - en_chars
        
        total_chars = len(text)
        if total_chars == 0:
            return TokenCountResult(count=0, model=self.model, method="approximate", confidence=0.85)
        
        # 计算 token 数
        zh_tokens = zh_chars / self.QWEN_PARAMS["zh_avg_chars"]
        en_tokens = en_chars / self.QWEN_PARAMS["en_avg_chars"]
        other_tokens = other_chars / 4.0
        
        total_tokens = int(zh_tokens + en_tokens + other_tokens)
        
        return TokenCountResult(
            count=total_tokens,
            model=self.model,
            method="approximate",
            confidence=0.85
        )


class UniversalTokenCounter(BaseTokenCounter):
    """通用 Token 计数器
    
    根据模型自动选择最佳计数器
    """
    
    # 模型到计数器的映射
    MODEL_MAPPING = {
        "gpt-4": ("tiktoken", "cl100k_base"),
        "gpt-4o": ("tiktoken", "cl100k_base"),
        "gpt-3.5-turbo": ("tiktoken", "cl100k_base"),
        "glm-4": ("glm", "glm-4"),
        "glm-3": ("glm", "glm-3"),
        "qwen": ("qwen", "qwen"),
        "qwen-2": ("qwen", "qwen-2"),
    }
    
    def __init__(self, model: str = "glm-4"):
        self.model = model
        self.counter = self._create_counter()
    
    def _create_counter(self) -> BaseTokenCounter:
        """创建计数器"""
        counter_type, model_name = self.MODEL_MAPPING.get(self.model, ("glm", self.model))
        
        if counter_type == "tiktoken":
            counter = TiktokenCounter(model_name)
            if counter.is_available():
                return counter
            # fallback to GLM
            return GLMTokenCounter(self.model)
        elif counter_type == "glm":
            return GLMTokenCounter(model_name)
        elif counter_type == "qwen":
            return QwenTokenCounter(model_name)
        else:
            return GLMTokenCounter(self.model)
    
    def is_available(self) -> bool:
        return self.counter.is_available()
    
    def count(self, text: str) -> TokenCountResult:
        return self.counter.count(text)


class TokenCounter:
    """Token 计数器（兼容旧接口）
    
    统一接口，支持多模型
    """
    
    def __init__(self, model: str = "glm-4"):
        """初始化 Token 计数器
        
        Args:
            model: 模型名称 (gpt-4, glm-4, qwen 等)
        """
        self.model = model
        self.counter = UniversalTokenCounter(model)
        
        # 缓存
        self._cache: Dict[str, TokenCountResult] = {}
    
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
        cache_key = hashlib.md5(f"{self.model}:{text}".encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key].count
        
        # 计算
        result = self.counter.count(text)
        
        # 缓存结果
        self._cache[cache_key] = result
        return result.count
    
    def count_messages(self, messages: List[Dict]) -> int:
        """计算消息列表的 Token 数
        
        Args:
            messages: 消息列表
        
        Returns:
            Token 数量
        """
        total = 0
        
        for msg in messages:
            # 每条消息的基础开销
            total += 4
            
            content = msg.get("content", "")
            if isinstance(content, str):
                total += self.count_text(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        total += self.count_text(part["text"])
        
        # 对话基础开销
        total += 3
        
        return total
    
    def count_file(self, filepath: str) -> int:
        """计算文件的 Token 数"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.count_text(content)
        except Exception as e:
            print(f"❌ 无法读取文件 {filepath}: {e}", file=sys.stderr)
            return 0
    
    def get_count_result(self, text: str) -> TokenCountResult:
        """获取详细的计数结果
        
        Args:
            text: 要计算的文本
        
        Returns:
            TokenCountResult
        """
        return self.counter.count(text)
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Token 计数器 v1.2.0")
    parser.add_argument("input", help="要计算的文本或文件路径")
    parser.add_argument("--model", default="glm-4", help="模型名称 (gpt-4, glm-4, qwen)")
    parser.add_argument("--file", action="store_true", help="输入是文件路径")
    parser.add_argument("--json", action="store_true", help="输入是 JSON 格式的消息列表")
    parser.add_argument("--detail", action="store_true", help="显示详细信息")
    
    args = parser.parse_args()
    
    counter = TokenCounter(args.model)
    
    if args.file:
        count = counter.count_file(args.input)
        if args.detail:
            result = counter.get_count_result(open(args.input).read())
            print(f"Token 数: {result.count}")
            print(f"模型: {result.model}")
            print(f"方法: {result.method}")
            print(f"置信度: {result.confidence:.0%}")
        else:
            print(count)
    elif args.json:
        try:
            messages = json.loads(args.input)
            count = counter.count_messages(messages)
            print(count)
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        count = counter.count_text(args.input)
        if args.detail:
            result = counter.get_count_result(args.input)
            print(f"Token 数: {result.count}")
            print(f"模型: {result.model}")
            print(f"方法: {result.method}")
            print(f"置信度: {result.confidence:.0%}")
        else:
            print(count)


if __name__ == "__main__":
    main()
