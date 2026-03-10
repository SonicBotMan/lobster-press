#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TF-IDF 评分器 v1.2.1
基于 RFC #34 的 Zero-cost 本地评分方案

修复 Issue #51: 中文分词改用 bi-gram，提升 TF-IDF 效果

Layer 1 — TF-IDF（无依赖，纯本地）
Layer 2 — 结构性信号（规则，零成本）
Layer 3 — 时间衰减（连续函数）

Author: LobsterPress Team
Version: v1.2.1
"""

import sys
import re
import math
import time
from collections import Counter
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ScoredMessage:
    """评分后的消息"""
    role: str
    content: str
    timestamp: float
    tfidf_score: float = 0.0
    structural_bonus: float = 0.0
    time_decay: float = 0.0
    final_score: float = 0.0
    msg_type: str = "unknown"
    tokens: List[str] = None
    
    def __post_init__(self):
        if self.tokens is None:
            self.tokens = []


class TFIDFScorer:
    """TF-IDF 评分器
    
    基于 RFC #34 的三层叠加评分：
    - Layer 1: TF-IDF（词汇稀有度）
    - Layer 2: 结构性信号（规则）
    - Layer 3: 时间衰减
    """
    
    # 结构性信号规则
    STRUCTURAL_SIGNALS = [
        # (分数, 正则表达式列表)
        (+30, [r'```', r'`[^`]+`']),              # 代码块 → 强保留
        (+25, [r'error|exception|bug|报错|失败']), # 错误信息
        (+20, [r'决定|采用|chosen|will use|就用']), # 决策语句
        (+18, [r'config|host|port|key|secret|配置']), # 配置信息
        (+15, [r'https?://', r'www\.']),          # URL
        (+12, [r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}']), # IP 地址
        (+10, [r'问题|question|如何|怎么|why']),   # 问题
        (-15, [r'^(好的|ok|嗯|👍|谢谢|got it|嗯嗯|哦哦)$']), # 闲聊降权
        (-10, [r'^(好|是|对|ok)$']),              # 简单确认降权
    ]
    
    def __init__(self):
        """初始化评分器"""
        self.idf_cache: Dict[str, float] = {}
        self.corpus_tokens: List[List[str]] = []
    
    def tokenize(self, text: str) -> List[str]:
        """分词（改进版，支持中文 bi-gram）
        
        修复 Issue #51: 中文按 bi-gram 切分，而非单字
        这样可以保留词汇的语义信息，提升 TF-IDF 效果
        
        Args:
            text: 输入文本
        
        Returns:
            Token 列表
        """
        tokens = []
        
        # 提取英文单词（保持不变）
        english_words = re.findall(r'[a-zA-Z]+', text.lower())
        tokens.extend(english_words)
        
        # 提取数字（保持不变）
        numbers = re.findall(r'\d+', text)
        tokens.extend(numbers)
        
        # 提取中文 bi-gram（修复 Issue #51）
        # 原来是单字：'数据库' → ['数', '据', '库']
        # 现在是 bi-gram：'数据库' → ['数据', '据库']
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        for i in range(len(chinese_chars) - 1):
            bi_gram = chinese_chars[i] + chinese_chars[i + 1]
            tokens.append(bi_gram)
        
        # 单字也保留（用于短词匹配）
        # 但权重会通过 IDF 自然降低
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
        
        # 计算文档频率
        df = Counter()
        for doc in corpus:
            for term in set(doc):
                df[term] += 1
        
        # 计算 IDF
        idf = {}
        for term, count in df.items():
            # 使用平滑公式：log((N+1)/(count+1)) + 1
            idf[term] = math.log((N + 1) / (count + 1)) + 1
        
        return idf
    
    def score_message(self, 
                      content: str, 
                      timestamp: float = 0,
                      role: str = "user") -> ScoredMessage:
        """对单条消息评分
        
        Args:
            content: 消息内容
            timestamp: 时间戳
            role: 角色
        
        Returns:
            评分后的消息
        """
        # 分词
        tokens = self.tokenize(content)
        
        # Layer 1: TF-IDF 基础分
        tfidf_score = 0.0
        if tokens and self.idf_cache:
            # 计算该消息的平均 IDF 值
            idf_values = [self.idf_cache.get(t, 1.0) for t in tokens]
            tfidf_score = sum(idf_values) / len(idf_values) * 10  # 缩放到 0-100
        
        # Layer 2: 结构性信号加成
        structural_bonus = self._compute_structural_bonus(content)
        
        # Layer 3: 时间衰减
        time_decay = 0.0
        if timestamp > 0:
            age_hours = (time.time() - timestamp) / 3600
            time_decay = -min(15, age_hours * 0.3)  # 最多衰减 15 分
        
        # 最终分数
        final_score = max(0, tfidf_score + structural_bonus + time_decay)
        
        # 判断消息类型
        msg_type = self._classify_message(content)
        
        return ScoredMessage(
            role=role,
            content=content,
            timestamp=timestamp,
            tfidf_score=tfidf_score,
            structural_bonus=structural_bonus,
            time_decay=time_decay,
            final_score=final_score,
            msg_type=msg_type,
            tokens=tokens,
        )
    
    def score_messages(self, 
                       messages: List[Dict]) -> List[ScoredMessage]:
        """对消息列表评分
        
        Args:
            messages: 消息列表
        
        Returns:
            评分后的消息列表
        """
        # 先构建语料库并计算 IDF
        self.corpus_tokens = []
        for msg in messages:
            content = msg.get("content", "")
            tokens = self.tokenize(content)
            self.corpus_tokens.append(tokens)
        
        self.idf_cache = self.compute_idf(self.corpus_tokens)
        
        # 逐条评分
        scored = []
        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", 0)
            role = msg.get("role", "user")
            
            scored_msg = self.score_message(content, timestamp, role)
            scored.append(scored_msg)
        
        return scored
    
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
                    break  # 每个规则只匹配一次
        
        return total_bonus
    
    def _classify_message(self, content: str) -> str:
        """分类消息类型
        
        Args:
            content: 消息内容
        
        Returns:
            消息类型
        """
        content_lower = content.lower()
        
        # 决策
        if re.search(r'决定|采用|chosen|will use|就用|确定', content_lower):
            return "decision"
        
        # 错误
        if re.search(r'error|exception|bug|报错|失败|问题', content_lower):
            return "error"
        
        # 配置
        if re.search(r'config|host|port|key|secret|配置|设置', content_lower):
            return "config"
        
        # 代码
        if re.search(r'```|`[^`]+`|function|def |class ', content_lower):
            return "code"
        
        # 问题
        if re.search(r'\?|？|如何|怎么|为什么|why|how', content_lower):
            return "question"
        
        # 闲聊
        if re.search(r'^(好的|ok|嗯|👍|谢谢|got it|嗯嗯|哦哦|好|是|对)$', content_lower.strip()):
            return "chitchat"
        
        return "unknown"


def main():
    """命令行入口"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="TF-IDF 评分器 v1.2.1")
    parser.add_argument("input_file", help="输入文件（JSON 格式的消息列表）")
    parser.add_argument("--top", type=int, default=10, help="显示前 N 条高分消息")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    
    args = parser.parse_args()
    
    # 读取输入
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            messages = json.load(f)
    except Exception as e:
        print(f"❌ 无法读取输入文件: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 评分
    scorer = TFIDFScorer()
    scored = scorer.score_messages(messages)
    
    # 按分数排序
    sorted_scored = sorted(scored, key=lambda m: m.final_score, reverse=True)
    
    # 输出
    if args.json:
        output = []
        for msg in sorted_scored[:args.top]:
            output.append({
                "role": msg.role,
                "content": msg.content[:100],
                "final_score": round(msg.final_score, 2),
                "tfidf_score": round(msg.tfidf_score, 2),
                "structural_bonus": round(msg.structural_bonus, 2),
                "time_decay": round(msg.time_decay, 2),
                "msg_type": msg.msg_type,
            })
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"\n📊 Top {args.top} 高分消息（v1.2.1 - 中文 bi-gram）:\n")
        for i, msg in enumerate(sorted_scored[:args.top], 1):
            print(f"{i}. [{msg.msg_type}] 分数: {msg.final_score:.1f}")
            print(f"   TF-IDF: {msg.tfidf_score:.1f} | 结构: {msg.structural_bonus:+.1f} | 衰减: {msg.time_decay:.1f}")
            print(f"   内容: {msg.content[:80]}...")
            print()


if __name__ == "__main__":
    main()
