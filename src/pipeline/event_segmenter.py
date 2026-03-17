#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Event Segmenter - 情节边界检测

基于 EM-LLM (ICLR 2025) 的情节分割理论：
- 话题突变（TF-IDF 余弦相似度骤降）
- 时间断层（消息间隔 > threshold）
- 显式边界信号（system 消息、角色重置等）

Author: LobsterPress Team
Version: v2.6.0
"""

import re
import math
from typing import List, Dict
from datetime import datetime
from collections import Counter


class EventSegmenter:
    """
    将消息序列切分为语义连贯的「情节」（episode）。
    每个情节独立压缩为一个叶子摘要，保证摘要内部话题一致性。
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.25,  # 低于此值判定为话题突变
        time_gap_seconds: int = 3600,         # 超过 1 小时判定为时间断层
        min_episode_tokens: int = 500,        # 情节最小 token 数（防止过度分割）
        max_episode_tokens: int = 20000,      # 情节最大 token 数（硬上限）
    ):
        self.similarity_threshold = similarity_threshold
        self.time_gap_seconds = time_gap_seconds
        self.min_episode_tokens = min_episode_tokens
        self.max_episode_tokens = max_episode_tokens
    
    def segment(self, messages: List[Dict]) -> List[List[Dict]]:
        """
        将消息列表分割为情节列表。
        
        Args:
            messages: 按 seq 排序的消息列表
        
        Returns:
            情节列表，每个情节是一个消息列表
        """
        if not messages:
            return []
        if len(messages) == 1:
            return [messages]
        
        boundaries = self._detect_boundaries(messages)
        return self._split_by_boundaries(messages, boundaries)
    
    def _detect_boundaries(self, messages: List[Dict]) -> List[int]:
        """
        返回边界位置索引列表（边界 = 新情节的起始索引）。
        索引 0 始终是边界（第一个情节的开始）。
        """
        boundaries = [0]
        episode_tokens = 0  # v2.6.0: 累计当前情节的 token 数
        
        for i in range(1, len(messages)):
            prev = messages[i - 1]
            curr = messages[i]
            curr_tokens = self._estimate_tokens(curr.get('content', ''))
            
            if self._is_boundary(prev, curr, messages, i, episode_tokens + curr_tokens):
                boundaries.append(i)
                episode_tokens = 0  # 重置计数器
            else:
                episode_tokens += curr_tokens
        
        return boundaries
    
    def _is_boundary(self, prev: Dict, curr: Dict,
                     messages: List[Dict], idx: int,
                     episode_tokens: int) -> bool:
        """判断 prev -> curr 之间是否存在情节边界
        
        Args:
            prev: 前一条消息
            curr: 当前消息
            messages: 完整消息列表
            idx: 当前消息索引
            episode_tokens: 从上一个边界到当前的累计 token 数（v2.6.0 优化）
        """
        
        # 1. 显式边界：system 消息（角色切换、对话重置）
        if curr.get('role') == 'system':
            return True
        
        # 2. 时间断层
        time_gap = self._get_time_gap(prev, curr)
        if time_gap is not None and time_gap > self.time_gap_seconds:
            return True
        
        # 3. 话题突变（TF-IDF 余弦距离）
        prev_content = prev.get('content', '')
        curr_content = curr.get('content', '')
        if len(prev_content) > 20 and len(curr_content) > 20:
            similarity = self._cosine_similarity(
                self._tokenize(prev_content),
                self._tokenize(curr_content)
            )
            if similarity < self.similarity_threshold:
                return True
        
        # 4. 硬上限：当前情节累计 token 超过 max_episode_tokens
        # v2.6.0 优化：使用真实累计 token 而非固定窗口
        if episode_tokens > self.max_episode_tokens:
            return True
        
        return False
    
    def _split_by_boundaries(self, messages: List[Dict],
                              boundaries: List[int]) -> List[List[Dict]]:
        """按边界索引切分消息列表，并合并过小的情节"""
        episodes = []
        boundaries_set = set(boundaries)
        
        current_episode = []
        for i, msg in enumerate(messages):
            if i in boundaries_set and current_episode:
                episodes.append(current_episode)
                current_episode = []
            current_episode.append(msg)
        
        if current_episode:
            episodes.append(current_episode)
        
        # 合并过小的情节（避免碎片化）
        return self._merge_small_episodes(episodes)
    
    def _merge_small_episodes(self,
                               episodes: List[List[Dict]]) -> List[List[Dict]]:
        """将 token 数不足 min_episode_tokens 的情节与前一个情节合并"""
        if not episodes:
            return episodes
        
        merged = [episodes[0]]
        for episode in episodes[1:]:
            episode_tokens = sum(
                self._estimate_tokens(m.get('content', ''))
                for m in episode
            )
            if episode_tokens < self.min_episode_tokens:
                merged[-1] = merged[-1] + episode  # 合并到前一个
            else:
                merged.append(episode)
        
        return merged
    
    def _get_time_gap(self, prev: Dict, curr: Dict) -> float | None:
        """获取两条消息间的时间差（秒），解析失败返回 None"""
        try:
            t1 = datetime.fromisoformat(
                prev.get('created_at') or prev.get('timestamp', '')
            )
            t2 = datetime.fromisoformat(
                curr.get('created_at') or curr.get('timestamp', '')
            )
            return abs((t2 - t1).total_seconds())
        except Exception:
            return None
    
    def _tokenize(self, text: str) -> Counter:
        """简单分词（支持中英文），返回词频 Counter"""
        # 中文按字切分，英文按单词切分
        words = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]{2,}', text.lower())
        return Counter(words)
    
    def _cosine_similarity(self, a: Counter, b: Counter) -> float:
        """计算两个词频向量的余弦相似度"""
        if not a or not b:
            return 0.0
        
        common = set(a.keys()) & set(b.keys())
        dot = sum(a[w] * b[w] for w in common)
        norm_a = math.sqrt(sum(v ** 2 for v in a.values()))
        norm_b = math.sqrt(sum(v ** 2 for v in b.values()))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
    
    def _estimate_tokens(self, text: str) -> int:
        """粗估 token 数（与 database.py 保持一致）"""
        chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        return int((len(text) - chinese) / 4 + chinese / 1.5)


# ==================== 单元测试 ====================

if __name__ == '__main__':
    segmenter = EventSegmenter()
    
    # 构造测试数据：两个明显不同话题
    msgs_topic_a = [
        {'role': 'user', 'content': '帮我设计数据库表结构，需要存用户信息', 'created_at': '2026-03-17T10:00:00'},
        {'role': 'assistant', 'content': '好的，用户表需要 id, name, email 字段', 'created_at': '2026-03-17T10:01:00'},
        {'role': 'user', 'content': '还需要存用户的登录时间和 IP', 'created_at': '2026-03-17T10:02:00'},
    ]
    msgs_topic_b = [
        {'role': 'user', 'content': '我们聊聊今天的午饭吧，想吃火锅', 'created_at': '2026-03-17T12:00:00'},
        {'role': 'assistant', 'content': '火锅不错！推荐川式鸳鸯锅', 'created_at': '2026-03-17T12:01:00'},
    ]
    
    episodes = segmenter.segment(msgs_topic_a + msgs_topic_b)
    print(f'✅ 情节数: {len(episodes)}')
    for i, ep in enumerate(episodes):
        print(f'  情节 {i+1}: {len(ep)} 条消息')
        print(f'    第一条: {ep[0]["content"][:40]}...')
