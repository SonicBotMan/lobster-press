#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TF-IDF 评分器 v2.5.0（标准化接口）
从 scripts/tfidf_scorer.py 提升，适配 v2.5.0 架构

新增：
- score_and_tag() 批量接口
- compression_exempt 字段
- EXEMPT_TYPES 定义

Author: LobsterPress Team
Version: v2.5.0
"""

import re
import math
import time
from datetime import datetime
from collections import Counter
from typing import List, Dict, Union
from dataclasses import dataclass


# 压缩豁免的消息类型（这些类型的消息不应被 DAG 折叠）
EXEMPT_TYPES = {"decision", "config", "code", "error"}


def parse_timestamp(ts: Union[str, int, float, None]) -> float:
    """解析时间戳（支持 ISO 8601 和数值格式）
    
    Args:
        ts: 时间戳（字符串、数值或 None）
    
    Returns:
        Unix 时间戳（秒）
    """
    if ts is None:
        return 0.0
    
    if isinstance(ts, (int, float)):
        return max(0.0, float(ts)) if ts >= 0 else 0.0
    
    if isinstance(ts, str):
        try:
            return float(ts)
        except ValueError:
            pass
        
        iso_formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
        ]
        
        for fmt in iso_formats:
            try:
                dt = datetime.strptime(ts, fmt)
                return dt.timestamp()
            except ValueError:
                continue
        
        return 0.0
    
    return 0.0


@dataclass
class ScoredMessage:
    """评分后的消息（v2.5.0 标准格式）"""
    id: str
    role: str
    content: str
    timestamp: float
    msg_type: str = "unknown"
    tfidf_score: float = 0.0
    structural_bonus: float = 0.0
    time_decay: float = 0.0
    final_score: float = 0.0
    compression_exempt: bool = False
    tokens: List[str] = None
    
    def __post_init__(self):
        if self.tokens is None:
            self.tokens = []


class TFIDFScorer:
    """v2.5.0 标准化评分器
    
    三层叠加评分：
    - Layer 1: TF-IDF（词汇稀有度）
    - Layer 2: 结构性信号（规则）
    - Layer 3: 时间衰减
    
    新增：
    - compression_exempt 字段（基于 msg_type 判断）
    - score_and_tag() 批量接口
    """
    
    STRUCTURAL_SIGNALS = [
        (+30, [r'```', r'`[^`]+`']),
        (+25, [r'error|exception|bug|报错|失败']),
        (+20, [r'决定|采用|chosen|will use|就用']),
        (+18, [r'config|host|port|key|secret|配置']),
        (+15, [r'https?://', r'www\.']),
        (+12, [r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}']),
        (+10, [r'问题|question|如何|怎么|why']),
        (-15, [r'^(好的|ok|嗯|👍|谢谢|got it|嗯嗯|哦哦)$']),
        (-10, [r'^(好|是|对|ok)$']),
    ]
    
    def __init__(self):
        """初始化评分器"""
        self.idf_cache: Dict[str, float] = {}
        self.corpus_tokens: List[List[str]] = []
    
    def tokenize(self, text: str) -> List[str]:
        """分词（支持中文 bi-gram）
        
        Args:
            text: 输入文本
        
        Returns:
            Token 列表
        """
        tokens = []
        
        # 英文单词
        english_words = re.findall(r'[a-zA-Z]+', text.lower())
        tokens.extend(english_words)
        
        # 数字
        numbers = re.findall(r'\d+', text)
        tokens.extend(numbers)
        
        # 中文 bi-gram
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        for i in range(len(chinese_chars) - 1):
            bi_gram = chinese_chars[i] + chinese_chars[i + 1]
            tokens.append(bi_gram)
        
        # 单字也保留
        tokens.extend(chinese_chars)
        
        return tokens
    
    def compute_idf(self, corpus: List[List[str]]) -> Dict[str, float]:
        """计算 IDF 值
        
        Args:
            corpus: 语料库（每个文档的 token 列表）
        
        Returns:
            词到 IDF 值的映射
        """
        N = len(corpus)
        if N == 0:
            return {}
        
        df = Counter()
        for doc in corpus:
            for term in set(doc):
                df[term] += 1
        
        idf = {}
        for term, count in df.items():
            idf[term] = math.log((N + 1) / (count + 1)) + 1
        
        return idf
    
    def score_and_tag(self, messages: List[Dict]) -> List[ScoredMessage]:
        """批量评分并打标签（v2.5.0 核心接口）
        
        供 IncrementalCompressor 在入库前调用
        
        Args:
            messages: 原始消息列表，每条格式 {id, role, content, timestamp}
        
        Returns:
            ScoredMessage 列表，含 msg_type 和 compression_exempt
        """
        # 先构建语料库并计算 IDF
        self.corpus_tokens = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                # 提取文本内容
                texts = []
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        texts.append(block.get('text', ''))
                content = ' '.join(texts)
            
            tokens = self.tokenize(str(content))
            self.corpus_tokens.append(tokens)
        
        self.idf_cache = self.compute_idf(self.corpus_tokens)
        
        # 逐条评分
        results = []
        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            if isinstance(content, list):
                texts = []
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        texts.append(block.get('text', ''))
                content = ' '.join(texts)
            else:
                content = str(content)
            
            timestamp = msg.get("timestamp", 0)
            role = msg.get("role", "user")
            
            # 解析时间戳
            ts = parse_timestamp(timestamp)
            
            # 分词
            tokens = self.corpus_tokens[i]
            
            # Layer 1: TF-IDF 基础分
            tfidf_score = 0.0
            if tokens and self.idf_cache:
                idf_values = [self.idf_cache.get(t, 1.0) for t in tokens]
                tfidf_score = sum(idf_values) / len(idf_values) * 10
            
            # Layer 2: 结构性信号加成
            structural_bonus = self._compute_structural_bonus(content)
            
            # Layer 3: 时间衰减
            time_decay = 0.0
            if ts > 0:
                age_hours = (time.time() - ts) / 3600
                if age_hours > 0:
                    time_decay = -min(15, age_hours * 0.3)
            
            # 最终分数
            final_score = max(0, tfidf_score + structural_bonus + time_decay)
            
            # 判断消息类型
            msg_type = self._classify_message(content)
            
            # 判断是否豁免压缩
            compression_exempt = msg_type in EXEMPT_TYPES
            
            results.append(ScoredMessage(
                id=msg.get("id", f"msg_{i}"),
                role=role,
                content=content,
                timestamp=ts,
                msg_type=msg_type,
                tfidf_score=round(tfidf_score, 2),
                structural_bonus=round(structural_bonus, 2),
                time_decay=round(time_decay, 2),
                final_score=round(final_score, 2),
                compression_exempt=compression_exempt,
                tokens=tokens,
            ))
        
        return results
    
    def score_messages(self, messages: List[Dict]) -> List[ScoredMessage]:
        """对消息列表评分（兼容旧接口）
        
        Args:
            messages: 消息列表
        
        Returns:
            评分后的消息列表
        """
        return self.score_and_tag(messages)
    
    def _compute_structural_bonus(self, content: str) -> float:
        """计算结构性信号加成
        
        Args:
            content: 消息内容
        
        Returns:
            结构性加成分数
        """
        total_bonus = 0.0
        content_lower = content.lower()
        
        for bonus, patterns in self.STRUCTURAL_SIGNALS:
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    total_bonus += bonus
                    break
        
        return total_bonus
    
    def _classify_message(self, content: str) -> str:
        """分类消息类型
        
        Args:
            content: 消息内容
        
        Returns:
            消息类型
        """
        content_lower = content.lower()
        
        if re.search(r'决定|采用|chosen|will use|就用|确定', content_lower):
            return "decision"
        
        if re.search(r'error|exception|bug|报错|失败', content_lower):
            return "error"
        
        if re.search(r'config|host|port|key|secret|配置|设置', content_lower):
            return "config"
        
        if re.search(r'```|`[^`]+`|function|def |class ', content_lower):
            return "code"
        
        if re.search(r'\?|？|如何|怎么|为什么|why|how', content_lower):
            return "question"
        
        if re.search(r'^(好的|ok|嗯|👍|谢谢|got it|嗯嗯|哦哦|好|是|对)$', content_lower.strip()):
            return "chitchat"
        
        return "unknown"


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("🧪 测试 TFIDFScorer v2.5.0\n")
    
    scorer = TFIDFScorer()
    
    # 测试消息
    test_messages = [
        {"id": "m1", "role": "user", "content": "我们决定采用 React + Node.js 方案", "timestamp": 0},
        {"id": "m2", "role": "user", "content": "好的", "timestamp": 0},
        {"id": "m3", "role": "assistant", "content": "```python\ndef hello(): pass\n```", "timestamp": 0},
        {"id": "m4", "role": "user", "content": "配置 host=192.168.1.1 port=8080", "timestamp": 0},
        {"id": "m5", "role": "user", "content": "报错：Connection refused", "timestamp": 0},
    ]
    
    scored = scorer.score_and_tag(test_messages)
    
    print(f"{'ID':<5} {'类型':<10} {'豁免':<6} {'分数':<8} 内容（前40字）")
    print("-" * 80)
    for msg in scored:
        exempt = "✅" if msg.compression_exempt else "❌"
        print(f"{msg.id:<5} {msg.msg_type:<10} {exempt:<6} {msg.final_score:<8.1f} {msg.content[:40]}")
    
    print("\n✅ 测试完成")
