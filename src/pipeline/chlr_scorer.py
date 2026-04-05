#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHLRScorer — C-HLR+ 自适应半衰期回归算法

基于论文: "Contextual Half-Life Regression" (C-HLR+)
核心公式: h = base_h * (1 + α * complexity)

v4.0.96: 首次实现
"""

import math
from typing import Dict, List
from datetime import datetime, timedelta


class CHLRScorer:
    """
    C-HLR+ 价值评估器

    根据消息的复杂度、访问频率、时间衰减等因素计算半衰期和记忆强度。
    """

    def __init__(self, base_h: float = 12.0, alpha: float = 0.1):
        """
        初始化 C-HLR+ 评分器

        Args:
            base_h: 基础半衰期（小时），默认 12h
            alpha: 复杂度系数，默认 0.1
        """
        self.base_h = base_h
        self.alpha = alpha

    def calculate_complexity(self, message: Dict) -> float:
        """
        计算消息复杂度

        复杂度因素：
        - token_count：消息长度
        - entity_count：实体数量
        - tfidf_score：信息密度
        - has_code：是否包含代码

        Args:
            message: 消息对象

        Returns:
            复杂度分数 0-1
        """
        complexity = 0.0

        # 1. Token 长度因素（0-0.3）
        token_count = message.get("token_count", 0)
        if token_count > 0:
            # 假设 500 tokens 为高复杂度
            complexity += min(0.3, token_count / 500 * 0.3)

        # 2. 实体数量因素（0-0.3）
        metadata = message.get("metadata", {})
        if isinstance(metadata, str):
            try:
                import json

                metadata = json.loads(metadata)
            except:
                metadata = {}

        entity_count = len(metadata.get("entities", []))
        if entity_count > 0:
            # 假设 10 个实体为高复杂度
            complexity += min(0.3, entity_count / 10 * 0.3)

        # 3. TF-IDF 分数因素（0-0.2）
        tfidf_score = message.get("tfidf_score", 0)
        if tfidf_score > 0:
            # TF-IDF 分数越高，复杂度越高
            complexity += min(0.2, tfidf_score * 0.2)

        # 4. 是否包含代码（0-0.2）
        content = message.get("content", "")
        if isinstance(content, str):
            # 检测代码块
            if "```" in content or "def " in content or "function " in content:
                complexity += 0.2

        return min(1.0, complexity)

    def calculate_half_life(self, message: Dict) -> float:
        """
        计算半衰期（小时）

        公式: h = base_h * (1 + α * complexity)

        Args:
            message: 消息对象

        Returns:
            半衰期（小时）
        """
        complexity = self.calculate_complexity(message)
        half_life = self.base_h * (1 + self.alpha * complexity)

        # 访问次数加成：每次访问增加 10% 半衰期
        access_count = message.get("access_count", 0)
        if access_count > 0:
            half_life *= 1 + 0.1 * min(access_count, 10)  # 最多 10 次加成

        return half_life

    def calculate_retention(
        self, message: Dict, current_time: datetime = None
    ) -> float:
        """
        计算记忆保留率（0-1）

        基于遗忘曲线: R = 2^(-t/h)
        其中:
        - R = 保留率
        - t = 距离上次访问的时间（小时）
        - h = 半衰期

        Args:
            message: 消息对象
            current_time: 当前时间（默认为 now）

        Returns:
            保留率 0-1
        """
        if current_time is None:
            current_time = datetime.utcnow()

        # 计算距离上次访问的时间（小时）
        last_accessed_str = message.get("last_accessed_at") or message.get("created_at")
        if not last_accessed_str:
            return 1.0  # 新消息，保留率 100%

        try:
            last_accessed = datetime.fromisoformat(
                last_accessed_str.replace("Z", "+00:00")
            )
            if last_accessed.tzinfo:
                last_accessed = last_accessed.replace(tzinfo=None)

            hours_since_access = (current_time - last_accessed).total_seconds() / 3600
        except:
            return 1.0

        # 计算半衰期
        half_life = self.calculate_half_life(message)

        # 遗忘曲线公式 (C-HLR+ 正确实现)
        # 根据半衰期定义：当 t = h 时，保留率应为 50%
        # 正确公式: R = 2^(-t/h) = 0.5^(t/h)
        # 错误公式: R = e^(-t/h) 会导致 12 小时后只剩 36.8% 而非 50%
        if half_life <= 0:
            return 0.0

        retention = 0.5 ** (hours_since_access / half_life)

        return retention

    def should_promote(self, message: Dict, age_hours: float = None) -> bool:
        """
        判断是否应该晋升到下一层

        晋升条件：
        - working → episodic: 保留率 > 0.7 且有明确意图
        - episodic → semantic: 保留率 > 0.8 且访问次数 >= 3

        Args:
            message: 消息对象
            age_hours: 消息年龄（小时），默认自动计算

        Returns:
            是否应该晋升
        """
        retention = self.calculate_retention(message)

        current_tier = message.get("memory_tier", "working")
        access_count = message.get("access_count", 0)

        if current_tier == "working":
            # working → episodic: 保留率 > 0.7
            return retention > 0.7
        elif current_tier == "episodic":
            # episodic → semantic: 保留率 > 0.8 且访问次数 >= 3
            return retention > 0.8 and access_count >= 3
        else:
            # semantic 不再晋升
            return False

    def should_decay(self, message: Dict, threshold: float = 0.3) -> bool:
        """
        判断是否应该衰减（标记为 decayed）

        衰减条件：
        - 保留率 < 阈值（默认 0.3）

        Args:
            message: 消息对象
            threshold: 保留率阈值

        Returns:
            是否应该衰减
        """
        retention = self.calculate_retention(message)
        return retention < threshold

    def batch_calculate(self, messages: List[Dict]) -> List[Dict]:
        """
        批量计算消息的半衰期和保留率

        Args:
            messages: 消息列表

        Returns:
            带有 half_life 和 retention 字段的消息列表
        """
        results = []
        for msg in messages:
            msg_copy = msg.copy()
            msg_copy["half_life"] = self.calculate_half_life(msg)
            msg_copy["retention"] = self.calculate_retention(msg)
            results.append(msg_copy)

        return results
