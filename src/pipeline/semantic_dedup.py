#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语义去重器 v2.5.0（标准化接口）
从 scripts/semantic_dedup.py 提升，适配 v2.5.0 架构

新增：
- 支持 compression_exempt 消息跳过去重
- 标准化接口 deduplicate()

Author: LobsterPress Team
Version: v2.5.0
"""

import math
from typing import List, Tuple, Set
from collections import Counter

try:
    from .tfidf_scorer import ScoredMessage
except ImportError:
    # 直接运行时的导入
    from tfidf_scorer import ScoredMessage


class SemanticDeduplicator:
    """v2.5.0 语义去重器
    
    基于 TF 向量余弦相似度，阈值 0.82，零 API 成本。
    
    新增：
    - compression_exempt=True 的消息跳过去重，保证关键信息不被合并
    """
    
    def __init__(self, threshold: float = 0.82):
        """初始化去重器
        
        Args:
            threshold: 重复阈值（0-1）
        """
        self.threshold = threshold
        self.min_tokens = 3
    
    def deduplicate(self, scored: List[ScoredMessage]) -> Tuple[List[ScoredMessage], List[str]]:
        """去重
        
        Args:
            scored: ScoredMessage 列表（已评分）
        
        Returns:
            (保留的消息列表, 被删除的消息ID列表)
            
        Note:
            compression_exempt=True 的消息强制保留，不参与去重
        """
        to_remove: Set[str] = set()
        n = len(scored)
        
        # 缓存 token 列表
        tokens_cache = {msg.id: msg.tokens if msg.tokens else self._tokenize(msg.content) 
                        for msg in scored}
        
        for i in range(n):
            msg_a = scored[i]
            
            if msg_a.id in to_remove:
                continue
            
            # ✨ 豁免消息跳过去重
            if msg_a.compression_exempt:
                continue
            
            tokens_a = tokens_cache[msg_a.id]
            if len(tokens_a) < self.min_tokens:
                continue
            
            for j in range(i + 1, n):
                msg_b = scored[j]
                
                if msg_b.id in to_remove:
                    continue
                
                # ✨ 豁免消息跳过去重
                if msg_b.compression_exempt:
                    continue
                
                tokens_b = tokens_cache[msg_b.id]
                if len(tokens_b) < self.min_tokens:
                    continue
                
                # 计算余弦相似度
                sim = self._cosine(tokens_a, tokens_b)
                
                if sim > self.threshold:
                    # 保留分数更高的
                    if msg_a.final_score >= msg_b.final_score:
                        to_remove.add(msg_b.id)
                    else:
                        to_remove.add(msg_a.id)
                        break  # i 被删除，不需要继续比较
        
        kept = [m for m in scored if m.id not in to_remove]
        removed_ids = list(to_remove)
        
        return kept, removed_ids
    
    def _tokenize(self, text: str) -> List[str]:
        """简单分词（用于去重）
        
        Args:
            text: 输入文本
        
        Returns:
            Token 列表
        """
        import re
        tokens = re.findall(r'[a-zA-Z]+', text.lower())
        chinese = re.findall(r'[\u4e00-\u9fff]', text)
        for i in range(len(chinese) - 1):
            tokens.append(chinese[i] + chinese[i + 1])
        return tokens
    
    def _cosine(self, a: List[str], b: List[str]) -> float:
        """计算余弦相似度（基于 TF 向量）
        
        Args:
            a: 消息 A 的 token 列表
            b: 消息 B 的 token 列表
        
        Returns:
            相似度（0-1）
        """
        if not a or not b:
            return 0.0
        
        tf_a = Counter(a)
        tf_b = Counter(b)
        
        all_terms = set(tf_a) | set(tf_b)
        
        dot_product = sum(tf_a.get(t, 0) * tf_b.get(t, 0) for t in all_terms)
        
        norm_a = math.sqrt(sum(v ** 2 for v in tf_a.values()))
        norm_b = math.sqrt(sum(v ** 2 for v in tf_b.values()))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    import sys
    from pathlib import Path
    # 添加父目录到 sys.path，支持相对导入
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipeline.tfidf_scorer import TFIDFScorer
    
    print("🧪 测试 SemanticDeduplicator v2.5.0\n")
    
    scorer = TFIDFScorer()
    deduper = SemanticDeduplicator(threshold=0.82)
    
    # 测试消息
    test_messages = [
        {"id": "m1", "role": "user", "content": "我们决定采用 PostgreSQL", "timestamp": 0},
        {"id": "m2", "role": "user", "content": "我们决定使用 PostgreSQL 数据库", "timestamp": 1},
        {"id": "m3", "role": "user", "content": "Python 如何连接数据库", "timestamp": 2},
        {"id": "m4", "role": "user", "content": "Python 怎么连接数据库", "timestamp": 3},
    ]
    
    # 评分
    scored = scorer.score_and_tag(test_messages)
    
    print("评分结果:")
    for msg in scored:
        exempt = "✅" if msg.compression_exempt else "❌"
        print(f"  {msg.id}: [{msg.msg_type}] {exempt} 分数={msg.final_score:.1f}")
    
    print("\n去重:")
    kept, removed = deduper.deduplicate(scored)
    
    print(f"  保留: {len(kept)} 条")
    print(f"  删除: {len(removed)} 条")
    
    if removed:
        print(f"  被删除的 ID: {removed}")
    
    print("\n✅ 测试完成")
