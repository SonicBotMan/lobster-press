#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Embedding 去重增强器 v1.5.0
Issue #77 - Embedding 去重增强

基于语义 Embedding 的去重器，替代 TF 词频余弦相似度方案
"""

import sys
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# 检查依赖是否可用
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    print("⚠️ sentence-transformers 不可用，使用 fallback", file=sys.stderr)


@dataclass
class DuplicatePair:
    """重复消息对"""
    idx_a: int
    idx_b: int
    similarity: float
    kept_idx: int
    removed_idx: int


class EmbeddingDeduplicator:
    """基于 Embedding 的语义去重器
    
    使用 sentence-transformers 模型计算语义相似度
    相比 TF 词频方案，可以识别"语义相近但用词不同"的重复消息
    
    示例：
        "帮我写个函数" 和 "写一段代码实现这个功能"
        TF 方案：相似度 0.2（词汇不重叠）
        Embedding 方案：相似度 0.92（语义相同）
    """
    
    # 默认模型（轻量级，22MB）
    DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    
    # 重复阈值
    DEFAULT_THRESHOLD = 0.85
    
    def __init__(self, 
                 model_name: Optional[str] = None,
                 threshold: float = DEFAULT_THRESHOLD):
        """初始化去重器
        
        Args:
            model_name: 模型名称（None 使用默认模型）
            threshold: 重复阈值（0-1）
        """
        self.threshold = threshold
        self.model = None
        self.model_name = model_name or self.DEFAULT_MODEL
        
        if EMBEDDING_AVAILABLE:
            try:
                self.model = SentenceTransformer(self.model_name)
                print(f"✅ Embedding 模型已加载: {self.model_name}", file=sys.stderr)
            except Exception as e:
                print(f"⚠️ Embedding 模型加载失败: {e}", file=sys.stderr)
                print(f"   使用 fallback 方案", file=sys.stderr)
        else:
            print(f"⚠️ sentence-transformers 未安装", file=sys.stderr)
            print(f"   安装命令: pip install sentence-transformers", file=sys.stderr)
    
    def deduplicate(self, 
                    messages: List[Dict],
                    scores: List[float],
                    tokens_list: Optional[List[List[str]]] = None) -> Tuple[List[Dict], List[int]]:
        """去重
        
        Args:
            messages: 消息列表
            scores: 每条消息的重要性分数
            tokens_list: 兼容参数（EmbeddingDeduplicator 不使用，由 Embedding 替代）
        
        Returns:
            (去重后的消息列表, 被删除的消息索引列表)
        """
        if not self.model:
            # Fallback：使用原始 TF 方案
            return self._fallback_deduplicate(messages, scores)
        
        # 使用 Embedding 方案
        return self._embedding_deduplicate(messages, scores)
    
    def _embedding_deduplicate(self, 
                                messages: List[Dict],
                                scores: List[float]) -> Tuple[List[Dict], List[int]]:
        """使用 Embedding 去重"""
        # 提取文本
        texts = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                # 处理多部分内容
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                texts.append(" ".join(text_parts))
            else:
                texts.append(str(content))
        
        # 计算 Embeddings
        embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=False)
        
        # 归一化
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings_normalized = embeddings / norms
        
        # 计算相似度矩阵
        similarity_matrix = np.dot(embeddings_normalized, embeddings_normalized.T)
        
        # 找出重复消息
        to_remove = set()
        duplicate_pairs: List[DuplicatePair] = []
        
        n = len(messages)
        for i in range(n):
            if i in to_remove:
                continue
            
            for j in range(i + 1, n):
                if j in to_remove:
                    continue
                
                similarity = similarity_matrix[i][j]
                
                if similarity > self.threshold:
                    # 保留分数更高的消息
                    if scores[i] >= scores[j]:
                        to_remove.add(j)
                        duplicate_pairs.append(DuplicatePair(
                            idx_a=i,
                            idx_b=j,
                            similarity=similarity,
                            kept_idx=i,
                            removed_idx=j
                        ))
                    else:
                        to_remove.add(i)
                        duplicate_pairs.append(DuplicatePair(
                            idx_a=i,
                            idx_b=j,
                            similarity=similarity,
                            kept_idx=j,
                            removed_idx=i
                        ))
                        break  # i 被删除，不需要继续比较
        
        # 过滤重复消息
        deduped = [msg for i, msg in enumerate(messages) if i not in to_remove]
        
        return deduped, sorted(list(to_remove))
    
    def _fallback_deduplicate(self, 
                              messages: List[Dict],
                              scores: List[float]) -> Tuple[List[Dict], List[int]]:
        """Fallback：使用简单的文本匹配"""
        # 简单的精确匹配去重
        seen_texts = set()
        to_remove = set()
        
        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            if isinstance(content, list):
                text = " ".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
            else:
                text = str(content)
            
            text_normalized = text.strip().lower()
            
            if text_normalized in seen_texts:
                to_remove.add(i)
            else:
                seen_texts.add(text_normalized)
        
        deduped = [msg for i, msg in enumerate(messages) if i not in to_remove]
        
        return deduped, sorted(list(to_remove))
    
    def get_duplicate_report(self, 
                              messages: List[Dict],
                              scores: List[float]) -> str:
        """生成去重报告"""
        deduped, removed = self.deduplicate(messages, scores)
        
        lines = [
            "📊 Embedding 去重报告",
            "",
            f"总消息数: {len(messages)}",
            f"重复消息数: {len(removed)}",
            f"去重方式: {'Embedding' if self.model else 'Fallback (精确匹配)'}",
            f"阈值: {self.threshold}",
            "",
        ]
        
        if removed:
            lines.append("被删除的消息索引:")
            for idx in removed[:10]:  # 最多显示 10 个
                content = messages[idx].get("content", "")[:50]
                lines.append(f"  #{idx}: {content}...")
            
            if len(removed) > 10:
                lines.append(f"  ... 还有 {len(removed) - 10} 条")
        
        return "\n".join(lines)


def main():
    """测试入口"""
    # 测试消息
    messages = [
        {"role": "user", "content": "帮我写一个 Python 函数"},
        {"role": "assistant", "content": "好的，我来帮你写"},
        {"role": "user", "content": "写一段代码实现这个功能"},  # 与消息 0 语义相似
        {"role": "assistant", "content": "这是一个示例代码"},
        {"role": "user", "content": "好的，收到了"},  # 与消息 1 语义相似
    ]
    
    scores = [0.7, 0.5, 0.6, 0.8, 0.3]
    
    print("📊 Embedding 去重测试:")
    print("=" * 80)
    
    deduplicator = EmbeddingDeduplicator(threshold=0.85)
    
    print(deduplicator.get_duplicate_report(messages, scores))
    
    print("\n" + "=" * 80)
    print("原始消息:")
    for i, msg in enumerate(messages):
        print(f"  {i}. [{msg['role']}] {msg['content'][:50]}")
    
    deduped, removed = deduplicator.deduplicate(messages, scores)
    
    print(f"\n去重后消息（移除了 {len(removed)} 条）:")
    for i, msg in enumerate(deduped):
        print(f"  {i}. [{msg['role']}] {msg['content'][:50]}")


if __name__ == "__main__":
    main()
