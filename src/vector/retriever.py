"""
混合检索器：FTS5 + Vector → RRF → MMR → Time Decay

借鉴 MemOS Recall pipeline:
  FTS5+Vector → RRF(k=60) → MMR(λ=0.7) → Decay(14d) → Normalize → Filter(≥0.45)

Version: v5.0.0
"""

import math
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class HybridRetriever:
    """混合检索器

    完整检索流程:
      Step 1: 双通道并行检索 (FTS5 + Vector)
      Step 2: RRF 融合
      Step 3: MMR 多样性重排
      Step 4: 时间衰减 (retrieval_half_life=14d)
      Step 5: 归一化 + 过滤 (min_score=0.45)
    """

    def __init__(self, db, embedder=None):
        """初始化混合检索器

        Args:
            db: LobsterDatabase 实例
            embedder: BaseEmbedder 实例 (用于向量检索)
        """
        self.db = db
        self.embedder = embedder

    def search(
        self,
        query: str,
        conversation_id: str = None,
        top_k: int = 6,
        min_score: float = 0.45,
    ) -> List[Dict]:
        """完整检索流程

        Pipeline: FTS5 + Vector → RRF → MMR → Decay → Normalize → Filter

        Args:
            query: 搜索查询文本
            conversation_id: 可选，限定会话 ID
            top_k: 返回最大结果数
            min_score: 最低分数阈值 (default 0.45)

        Returns:
            检索结果列表，每项包含 target_id, target_type, content, normalized_score
        """
        # Step 1: 双通道并行检索
        fts_results = self._fts_search(query, conversation_id)
        vec_results = self._vector_search(query, conversation_id)

        # Step 2: RRF 融合
        rrf_scores = self._rrf_fuse([fts_results, vec_results])

        # Step 3: MMR 多样性重排
        mmr_results = self._mmr_rerank(rrf_scores, top_k * 2)

        # Step 4: 时间衰减（retrieval_half_life=14d）
        decayed = self._apply_retrieval_decay(mmr_results)

        # Step 5: 归一化 + 过滤
        max_score = max((r["score"] for r in decayed), default=1.0)
        if max_score == 0:
            max_score = 1.0

        final = []
        for r in decayed:
            r["normalized_score"] = r["score"] / max_score
            if r["normalized_score"] >= min_score:
                final.append(r)

        return final[:top_k]

    def _fts_search(self, query: str, conversation_id: str = None) -> List[Dict]:
        """FTS5 关键词检索

        使用数据库现有的 search_messages 和 search_summaries 方法
        """
        results = []

        # 搜索消息
        msgs = self.db.search_messages(query, conversation_id=conversation_id, limit=50)
        for i, msg in enumerate(msgs):
            results.append(
                {
                    "target_id": msg["message_id"],
                    "target_type": "message",
                    "content": msg.get("content", ""),
                    "created_at": msg.get("created_at", ""),
                    "rank": i,
                    "source": "fts",
                }
            )

        # 搜索摘要
        sums = self.db.search_summaries(
            query, conversation_id=conversation_id, limit=50
        )
        for i, s in enumerate(sums):
            results.append(
                {
                    "target_id": s["summary_id"],
                    "target_type": "summary",
                    "content": s.get("content", ""),
                    "created_at": s.get("created_at", ""),
                    "rank": i,
                    "source": "fts",
                }
            )

        return results

    def _vector_search(self, query: str, conversation_id: str = None) -> List[Dict]:
        """向量语义检索

        使用 embedder 和 database.vector_search()
        """
        if not self.embedder or not self.embedder.is_available():
            return []

        vec = self.embedder.embed(query)
        results = self.db.vector_search(vec, top_k=50, conversation_id=conversation_id)

        return [
            {
                "target_id": r["target_id"],
                "target_type": r["target_type"],
                "score": r["score"],
                "content": "",  # 向量检索不返回内容
                "created_at": "",
                "source": "vector",
            }
            for r in results
        ]

    def _rrf_fuse(self, result_lists: List[List[Dict]], k: int = 60) -> Dict[str, Dict]:
        """RRF 融合

        Formula: RRF(d) = Σ 1/(k + rank_i(d) + 1)

        Args:
            result_lists: 各检索通道的结果列表
            k: RRF 常数（默认 60，与 MemOS 一致）

        Returns:
            {target_id: {score, target_type, content, created_at}}
        """
        fused = {}

        for results in result_lists:
            for rank, item in enumerate(results):
                tid = item["target_id"]
                rrf_score = 1.0 / (k + rank + 1)

                if tid not in fused:
                    fused[tid] = {
                        "target_id": tid,
                        "target_type": item["target_type"],
                        "content": item.get("content", ""),
                        "created_at": item.get("created_at", ""),
                        "score": 0.0,
                    }
                fused[tid]["score"] += rrf_score

        return fused

    def _mmr_rerank(
        self, candidates: Dict[str, Dict], top_k: int, lam: float = 0.7
    ) -> List[Dict]:
        """MMR 多样性重排

        Formula: MMR(d) = λ·rel(d) − (1−λ)·max_sim(d, d_s)

        λ=0.7: 偏向相关性（与 MemOS 一致）
        α=0.3: 分数地板值（极老内容仍保留 30% 分数）
        """
        if not candidates:
            return []

        # 按分数降序排列
        sorted_items = sorted(
            candidates.values(), key=lambda x: x["score"], reverse=True
        )

        selected = []
        remaining = list(sorted_items)

        while remaining and len(selected) < top_k:
            if not selected:
                selected.append(remaining.pop(0))
                continue

            best_idx = 0
            best_mmr = -float("inf")

            for i, cand in enumerate(remaining):
                rel = cand["score"]
                # 简化相似度：用内容长度归一化的重叠度
                max_sim = (
                    max(
                        self._text_similarity(cand["content"], s["content"])
                        for s in selected
                    )
                    if selected
                    else 0.0
                )
                mmr_score = lam * rel - (1 - lam) * max_sim

                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected

    def _apply_retrieval_decay(
        self, results: List[Dict], half_life_days: float = 14.0
    ) -> List[Dict]:
        """检索时间衰减

        Formula: final = score × (0.3 + 0.7 × 0.5^(t/14d))

        半衰期 14d（与 MemOS retrieval_half_life 一致）
        α=0.3 为地板值：极老内容仍保留 30% 分数
        """
        now = datetime.utcnow()

        for r in results:
            score = r.get("score", 0)
            created_at = r.get("created_at", "")

            if not created_at:
                r["score"] = score * 0.3  # 无时间戳，给地板值
                continue

            try:
                created = datetime.fromisoformat(created_at)
                t_days = max((now - created).total_seconds() / 86400.0, 0.0)
            except (ValueError, TypeError):
                t_days = 999.0

            decay = 0.3 + 0.7 * math.pow(0.5, t_days / half_life_days)
            r["score"] = score * decay

        return results

    def _text_similarity(self, a: str, b: str) -> float:
        """简单文本相似度（字符级 Jaccard）"""
        if not a or not b:
            return 0.0
        set_a = set(a[:200])
        set_b = set(b[:200])
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0
