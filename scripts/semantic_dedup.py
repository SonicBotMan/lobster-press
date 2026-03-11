#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语义去重器 v1.2.1
基于 RFC #34 的余弦相似度去重方案

修复 Issue #51: 使用真正的 TF 向量余弦相似度，而非 Jaccard 变体

功能：
- 基于 TF 向量的真正余弦相似度
- 检测语义相似的消息
- 保留重要性更高的消息
- 零 API 成本，纯本地计算

Author: LobsterPress Team
Version: v1.3.0
"""

import sys
import math
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass
from collections import Counter


@dataclass
class SimilarityResult:
    """相似度检测结果"""
    msg_a_idx: int
    msg_b_idx: int
    similarity: float
    is_duplicate: bool


class SemanticDeduplicator:
    """语义去重器
    
    基于 TF 向量的真正余弦相似度：
    - 相似度 > 0.82 视为重复
    - 保留重要性更高的消息
    - 完全本地计算，零 API 成本
    """
    
    # 重复阈值
    DUPLICATE_THRESHOLD = 0.82
    
    # 最小 token 数（太短的消息不检测重复）
    MIN_TOKENS = 3
    
    def __init__(self, threshold: float = 0.82):
        """初始化去重器
        
        Args:
            threshold: 重复阈值（0-1）
        """
        self.threshold = threshold
    
    def cosine_similarity(self, tokens_a: List[str], tokens_b: List[str]) -> float:
        """计算真正的余弦相似度（基于 TF 向量）
        
        修复 Issue #51: 原实现是 Jaccard 变体，现在是真正的余弦相似度
        
        公式: cos(A, B) = (A · B) / (||A|| * ||B||)
        其中 A 和 B 是 TF 向量
        
        Args:
            tokens_a: 消息 A 的 token 列表
            tokens_b: 消息 B 的 token 列表
        
        Returns:
            相似度（0-1）
        """
        if not tokens_a or not tokens_b:
            return 0.0
        
        # 构建 TF 向量
        tf_a = Counter(tokens_a)
        tf_b = Counter(tokens_b)
        
        # 所有词项
        all_terms = set(tf_a) | set(tf_b)
        
        # 计算点积
        dot_product = sum(tf_a.get(t, 0) * tf_b.get(t, 0) for t in all_terms)
        
        # 计算模长
        norm_a = math.sqrt(sum(v ** 2 for v in tf_a.values()))
        norm_b = math.sqrt(sum(v ** 2 for v in tf_b.values()))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def find_duplicates(self, 
                        messages: List[Dict],
                        tokens_list: List[List[str]],
                        scores: List[float]) -> Tuple[List[int], List[SimilarityResult]]:
        """找出重复消息
        
        Args:
            messages: 消息列表
            tokens_list: 每条消息的 token 列表
            scores: 每条消息的重要性分数
        
        Returns:
            (要删除的消息索引列表, 相似度检测结果列表)
        """
        n = len(messages)
        duplicates_to_remove: Set[int] = set()
        similarity_results: List[SimilarityResult] = []
        
        # 两两比较
        for i in range(n):
            if i in duplicates_to_remove:
                continue
            
            tokens_i = tokens_list[i]
            if len(tokens_i) < self.MIN_TOKENS:
                continue
            
            for j in range(i + 1, n):
                if j in duplicates_to_remove:
                    continue
                
                tokens_j = tokens_list[j]
                if len(tokens_j) < self.MIN_TOKENS:
                    continue
                
                # 计算相似度
                similarity = self.cosine_similarity(tokens_i, tokens_j)
                
                # 判断是否重复
                is_duplicate = similarity > self.threshold
                
                result = SimilarityResult(
                    msg_a_idx=i,
                    msg_b_idx=j,
                    similarity=similarity,
                    is_duplicate=is_duplicate,
                )
                similarity_results.append(result)
                
                if is_duplicate:
                    # 保留重要性更高的消息
                    if scores[i] >= scores[j]:
                        duplicates_to_remove.add(j)
                    else:
                        duplicates_to_remove.add(i)
                        break  # i 被删除，不需要继续比较
        
        return sorted(list(duplicates_to_remove)), similarity_results
    
    def deduplicate(self, 
                    messages: List[Dict],
                    tokens_list: List[List[str]],
                    scores: List[float]) -> Tuple[List[Dict], List[int]]:
        """去重
        
        Args:
            messages: 消息列表
            tokens_list: 每条消息的 token 列表
            scores: 每条消息的重要性分数
        
        Returns:
            (去重后的消息列表, 被删除的消息索引列表)
        """
        duplicates, _ = self.find_duplicates(messages, tokens_list, scores)
        
        # 过滤重复消息
        deduped = [msg for i, msg in enumerate(messages) if i not in duplicates]
        
        return deduped, duplicates
    
    def get_duplicate_report(self, 
                             messages: List[Dict],
                             tokens_list: List[List[str]],
                             scores: List[float]) -> str:
        """生成去重报告
        
        Args:
            messages: 消息列表
            tokens_list: 每条消息的 token 列表
            scores: 每条消息的重要性分数
        
        Returns:
            报告文本
        """
        duplicates, results = self.find_duplicates(messages, tokens_list, scores)
        
        lines = [
            f"📊 语义去重报告（v1.2.1 - 真正的余弦相似度）",
            f"",
            f"总消息数: {len(messages)}",
            f"重复消息数: {len(duplicates)}",
            f"",
        ]
        
        if duplicates:
            lines.append("被删除的消息:")
            for idx in duplicates:
                content = messages[idx].get("content", "")[:60]
                lines.append(f"  #{idx}: {content}...")
            
            lines.append("")
            lines.append("相似度详情:")
            for result in results:
                if result.is_duplicate:
                    msg_a = messages[result.msg_a_idx].get("content", "")[:40]
                    msg_b = messages[result.msg_b_idx].get("content", "")[:40]
                    lines.append(f"  #{result.msg_a_idx} ↔ #{result.msg_b_idx} ({result.similarity:.2%})")
                    lines.append(f"    A: {msg_a}...")
                    lines.append(f"    B: {msg_b}...")
        
        return "\n".join(lines)


def main():
    """命令行入口"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="语义去重器 v1.2.1")
    parser.add_argument("input_file", help="输入文件（JSON 格式的消息列表）")
    parser.add_argument("--threshold", type=float, default=0.82, help="重复阈值")
    parser.add_argument("--report", action="store_true", help="输出详细报告")
    parser.add_argument("--output", help="输出文件")
    
    args = parser.parse_args()
    
    # 读取输入
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 无法读取输入文件: {e}", file=sys.stderr)
        sys.exit(1)
    
    messages = data.get("messages", data)
    tokens_list = data.get("tokens_list", [])
    scores = data.get("scores", [50.0] * len(messages))
    
    # 去重
    deduplicator = SemanticDeduplicator(threshold=args.threshold)
    
    if args.report:
        print(deduplicator.get_duplicate_report(messages, tokens_list, scores))
    else:
        deduped, removed = deduplicator.deduplicate(messages, tokens_list, scores)
        
        result = {
            "original_count": len(messages),
            "deduped_count": len(deduped),
            "removed_count": len(removed),
            "removed_indices": removed,
            "messages": deduped,
        }
        
        output = json.dumps(result, indent=2, ensure_ascii=False)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"✅ 已写入 {args.output}", file=sys.stderr)
        else:
            print(output)


if __name__ == "__main__":
    main()
