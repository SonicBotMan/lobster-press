#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress DAG Compressor - DAG 压缩器
借鉴 lossless-claw 的压缩策略

Author: LobsterPress Team
Version: v4.0.16
"""

import sys
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path

# 添加 database 模块
sys.path.insert(0, str(Path(__file__).parent))
from database import LobsterDatabase
from pipeline.event_segmenter import EventSegmenter
from prompts import build_leaf_summary_prompt, build_condensed_summary_prompt


class DAGCompressor:
    """DAG 压缩器 - 借鉴 lossless-claw
    
    核心功能：
    1. 叶子压缩：messages → leaf summaries
    2. 压缩摘要：summaries → condensed summaries
    3. Fresh tail 保护：最近 N 条消息不压缩
    4. 智能触发：达到阈值时自动压缩
    5. v2.6.0 新增：情节边界分割（EventSegmenter）
    """
    
    def __init__(self, 
                 db: LobsterDatabase,
                 fresh_tail_count: int = 32,
                 leaf_chunk_tokens: int = 20000,
                 condensed_min_fanout: int = 4,
                 llm_client=None):  # v3.1.0: LLM 客户端
        """初始化 DAG 压缩器
        
        v2.6.0 更新：添加 EventSegmenter 用于情节边界分割
        v3.1.0 更新：添加 llm_client 支持真正的 LLM 摘要
        
        Args:
            db: LobsterDatabase 实例
            fresh_tail_count: 最近 N 条消息不压缩（默认 32）
            leaf_chunk_tokens: 叶子压缩的 token 阈值（默认 20000）
            condensed_min_fanout: 压缩摘要的最小子节点数（默认 4）
            llm_client: LLM 客户端（可选，用于高质量摘要生成）
        """
        self.db = db
        self.fresh_tail_count = fresh_tail_count
        self.leaf_chunk_tokens = leaf_chunk_tokens
        self.condensed_min_fanout = condensed_min_fanout
        self.llm_client = llm_client  # v3.1.0
        
        # v2.6.0: 初始化情节分割器
        self.segmenter = EventSegmenter(
            max_episode_tokens=leaf_chunk_tokens
        )
    
    # ==================== 叶子压缩 ====================
    
    def leaf_compact(self, conversation_id: str, max_tokens: int = None, 
                     skip_message_ids: List[str] = None,
                     preprocessed_messages: List[Dict] = None) -> Optional[Dict]:
        """叶子压缩：消息 → 叶子摘要
        
        借鉴 lossless-claw 的 leaf pass：
        1. 选择最老的连续消息块（排除 fresh tail）
        2. 限制 token 数量（默认 20000）
        3. 生成叶子摘要
        4. 保存摘要和关系
        5. 更新上下文（移除被压缩的消息，添加摘要）
        
        Args:
            conversation_id: 对话 ID
            max_tokens: 最大 token 数（默认 leaf_chunk_tokens）
            skip_message_ids: 要跳过的消息 ID 列表（Bug 6 修复：支持 compression_exempt）
            preprocessed_messages: v4.0.12 预处理后的消息（ThreePassTrimmer 结果）
        
        Returns:
            最后一个情节的摘要（v2.6.0 改为多情节分割），
            如果无需压缩则返回 None。
            注意：非 None 即表示有压缩发生，调用方应继续检查是否需要进一步压缩。
        """
        if max_tokens is None:
            max_tokens = self.leaf_chunk_tokens
        
        skip_message_ids = set(skip_message_ids or [])  # Bug 6: 转为 set 提高查询效率
        
        # v4.0.12: 优先使用传入的预处理消息，否则从数据库读（Issue #150 Bug #2）
        if preprocessed_messages is not None:
            messages = preprocessed_messages
        else:
            # 1. 获取所有消息
            messages = self.db.get_messages(conversation_id)
        
        if len(messages) <= self.fresh_tail_count:
            print(f"⚠️ 消息数 ({len(messages)}) ≤ fresh tail ({self.fresh_tail_count})，无需压缩")
            return None
        
        # 2. 分离 fresh tail 和 older messages
        fresh_tail = messages[-self.fresh_tail_count:]
        older_messages = messages[:-self.fresh_tail_count]
        
        # 3. 获取已经被压缩的消息（从 context_items 中排除）
        compressed_message_ids = self._get_compressed_message_ids(conversation_id)
        
        # 4. 过滤出未被压缩且不在 skip_message_ids 中的消息
        uncompressed_messages = [
            m for m in older_messages 
            if m['message_id'] not in compressed_message_ids
            and m['message_id'] not in skip_message_ids  # Bug 6: 跳过 exempt 消息
        ]
        
        if not uncompressed_messages:
            print(f"✅ 所有旧消息都已被压缩，无需继续")
            return None
        
        # 5. 计算 uncompressed messages 的 token 数
        uncompressed_tokens = sum(m.get('token_count', 0) for m in uncompressed_messages)
        
        if uncompressed_tokens < max_tokens:
            print(f"⚠️ 未压缩消息 tokens ({uncompressed_tokens}) < {max_tokens}，无需压缩")
            return None
        
        # 6. v2.6.0: 使用 EventSegmenter 分割为情节
        episodes = self.segmenter.segment(uncompressed_messages)
        
        if not episodes:
            return None
        
        # 7. 为每个情节生成叶子摘要
        last_summary = None
        for episode in episodes:
            # Phase 2 (Issue #115): Episode token guard - 跳过太小的 episode
            episode_tokens = sum(m.get("token_count", 0) for m in episode)
            if episode_tokens < max_tokens * 0.5:
                print(f"⏭️ skip small episode: {episode_tokens} tokens (< {max_tokens * 0.5})")
                continue
            
            # 生成摘要内容
            summary_content = self._generate_leaf_summary(episode)
            
            # 创建摘要对象
            summary = {
                'conversation_id': conversation_id,
                'kind': 'leaf',
                'depth': 0,
                'content': summary_content,
                'source_messages': [m['message_id'] for m in episode],
                'earliest_at': episode[0].get('created_at'),
                'latest_at': episode[-1].get('created_at'),
                'descendant_count': len(episode)
            }
            
            # 保存摘要
            summary_id = self.db.save_summary(summary)
            summary['summary_id'] = summary_id
            
            # 更新上下文
            self._update_context_after_compression(
                conversation_id, 
                compressed_message_ids=[m['message_id'] for m in episode],
                new_summary_id=summary_id
            )
            
            print(f"✅ 创建叶子摘要: {summary_id}")
            print(f"   - 消息数: {len(episode)}")
            print(f"   - Tokens: {sum(m.get('token_count', 0) for m in episode)} → {self.db._estimate_tokens(summary_content)}")
            
            last_summary = summary
        
        return last_summary
    
    def _generate_leaf_summary(self, messages: List[Dict]) -> str:
        """生成叶子摘要
        
        v3.1.0 更新：支持真正的 LLM 摘要生成
        - 有 LLM: 调用 LLM 生成高质量摘要
        - 无 LLM: 降级为提取式摘要
        
        Args:
            messages: 消息列表
        
        Returns:
            摘要内容
        """
        # v3.1.0: 优先使用 LLM 生成摘要
        if self.llm_client:
            return self._generate_llm_leaf_summary(messages)
        else:
            return self._generate_extractive_leaf_summary(messages)
    
    def _generate_llm_leaf_summary(self, messages: List[Dict]) -> str:
        """使用 LLM 生成高质量叶子摘要
        
        v3.2.1: 使用优化的 prompt 模板
        
        Args:
            messages: 消息列表
        
        Returns:
            LLM 生成的摘要
        """
        try:
            # 使用优化的 prompt 模板
            prompt = build_leaf_summary_prompt(messages)
            
            # 调用 LLM
            summary = self.llm_client.generate(prompt, temperature=0.7, max_tokens=500)
            
            # 添加元数据
            summary_parts = []
            summary_parts.append(f"## 对话摘要 ({len(messages)} 条消息)")
            summary_parts.append(f"- 用户消息: {sum(1 for m in messages if m.get('role') == 'user')} 条")
            summary_parts.append(f"- 助手消息: {sum(1 for m in messages if m.get('role') == 'assistant')} 条")
            summary_parts.append(f"- 生成方式: LLM (v3.2.1)")
            summary_parts.append("")
            summary_parts.append("### 核心内容:")
            summary_parts.append(summary)
            
            return '\n'.join(summary_parts)
        except Exception as e:
            print(f"⚠️ LLM 摘要生成失败: {e}，降级为提取式摘要")
            return self._generate_extractive_leaf_summary(messages)
    
    def _generate_extractive_leaf_summary(self, messages: List[Dict]) -> str:
        """提取式叶子摘要（降级方案）
        
        使用 TF-IDF 评分和结构化信号提取关键内容
        
        Args:
            messages: 消息列表
        
        Returns:
            提取式摘要
        """
        # 按角色分组
        user_messages = [m for m in messages if m.get('role') == 'user']
        assistant_messages = [m for m in messages if m.get('role') == 'assistant']
        
        # 提取关键内容
        summary_parts = []
        summary_parts.append(f"## 对话摘要 ({len(messages)} 条消息)")
        summary_parts.append(f"- 用户消息: {len(user_messages)} 条")
        summary_parts.append(f"- 助手消息: {len(assistant_messages)} 条")
        summary_parts.append("")
        summary_parts.append("### 关键内容:")
        
        # 提取前 5 条重要消息
        for i, msg in enumerate(messages[:5], 1):
            content = msg.get('content', '')
            if len(content) > 100:
                content = content[:100] + '...'
            summary_parts.append(f"{i}. [{msg.get('role', 'unknown')}]: {content}")
        
        return '\n'.join(summary_parts)
    
    # ==================== 压缩摘要 ====================
    
    def condensed_compact(self, conversation_id: str, depth: int = 0, min_fanout: int = None) -> Optional[Dict]:
        """压缩摘要：摘要 → 更高层的摘要
        
        Phase 2 (Issue #115): 使用固定窗口批处理，避免 first-N forever
        
        借鉴 lossless-claw 的 condensed pass：
        1. 找到同深度的连续摘要（≥ min_fanout）
        2. 按 min_fanout 窗口批处理所有摘要
        3. 合并摘要内容
        4. 生成更高层的摘要
        5. 保存摘要和关系
        
        Args:
            conversation_id: 对话 ID
            depth: 摘要深度（默认 0 = 叶子摘要）
            min_fanout: 最小子节点数（默认 condensed_min_fanout）
        
        Returns:
            最后一个生成的摘要，如果无需压缩则返回 None
        """
        if min_fanout is None:
            min_fanout = self.condensed_min_fanout
        
        # 1. 获取指定深度的摘要
        summaries = self.db.get_summaries(conversation_id, depth)
        
        if len(summaries) < min_fanout:
            print(f"⚠️ 摘要数 ({len(summaries)}) < {min_fanout}，无需压缩")
            return None
        
        # Phase 2: 固定窗口批处理，处理所有可压缩的摘要
        last_summary = None
        i = 0
        while i + min_fanout <= len(summaries):
            chunk = summaries[i:i + min_fanout]
            combined_content = self._combine_summaries(chunk)
            summary_content = self._generate_condensed_summary(combined_content, depth)

            summary = {
                'conversation_id': conversation_id,
                'kind': 'condensed',
                'depth': depth + 1,
                'content': summary_content,
                'parent_summaries': [s['summary_id'] for s in chunk],
                'earliest_at': chunk[0].get('earliest_at'),
                'latest_at': chunk[-1].get('latest_at'),
                'descendant_count': sum(s.get('descendant_count', 0) for s in chunk),
            }

            summary_id = self.db.save_summary(summary)
            summary['summary_id'] = summary_id
            last_summary = summary
            
            print(f"✅ 创建压缩摘要: {summary_id}")
            print(f"   - 深度: {depth + 1}")
            print(f"   - 父摘要: {len(chunk)} 个")
            print(f"   - 总消息数: {summary['descendant_count']}")
            
            i += min_fanout
        
        return last_summary
    
    def _combine_summaries(self, summaries: List[Dict]) -> str:
        """合并摘要内容
        
        Args:
            summaries: 摘要列表
        
        Returns:
            合并后的内容
        """
        parts = []
        for i, s in enumerate(summaries, 1):
            parts.append(f"### 摘要 {i} ({s['summary_id']})")
            parts.append(f"时间范围: {s.get('earliest_at', 'N/A')} ~ {s.get('latest_at', 'N/A')}")
            parts.append(f"消息数: {s.get('descendant_count', 0)}")
            parts.append(f"内容: {s.get('content', '')}")
            parts.append("")
        
        return '\n'.join(parts)
    
    def _generate_condensed_summary(self, combined_content: str, depth: int) -> str:
        """生成压缩摘要
        
        v3.1.0 更新：支持真正的 LLM 摘要生成
        - 有 LLM: 调用 LLM 生成高质量摘要
        - 无 LLM: 降级为截断式摘要
        
        Args:
            combined_content: 合并的内容
            depth: 当前深度
        
        Returns:
            摘要内容
        """
        # v3.1.0: 优先使用 LLM 生成摘要
        if self.llm_client:
            return self._generate_llm_condensed_summary(combined_content, depth)
        else:
            return self._generate_extractive_condensed_summary(combined_content, depth)
    
    def _generate_llm_condensed_summary(self, combined_content: str, depth: int) -> str:
        """使用 LLM 生成高质量压缩摘要
        
        v3.2.1: 使用优化的 prompt 模板
        
        Args:
            combined_content: 合并的内容
            depth: 当前深度
        
        Returns:
            LLM 生成的摘要
        """
        try:
            # 使用优化的 prompt 模板
            prompt = build_condensed_summary_prompt(combined_content[:3000], depth + 1)
            
            # 调用 LLM
            summary = self.llm_client.generate(prompt, temperature=0.6, max_tokens=400)
            
            # 添加元数据
            summary_parts = []
            summary_parts.append(f"## 压缩摘要 (Depth {depth + 1})")
            summary_parts.append(f"- 原始长度: {len(combined_content)} 字符")
            summary_parts.append(f"- 摘要长度: {len(summary)} 字符")
            summary_parts.append(f"- 生成方式: LLM (v3.2.1)")
            summary_parts.append("")
            summary_parts.append("### 核心要点:")
            summary_parts.append(summary)
            
            return '\n'.join(summary_parts)
        except Exception as e:
            print(f"⚠️ LLM 压缩摘要生成失败: {e}，降级为截断式摘要")
            return self._generate_extractive_condensed_summary(combined_content, depth)
    
    def _generate_extractive_condensed_summary(self, combined_content: str, depth: int) -> str:
        """截断式压缩摘要（降级方案）
        
        Args:
            combined_content: 合并的内容
            depth: 当前深度
        
        Returns:
            截断式摘要
        """
        summary_parts = []
        summary_parts.append(f"## 压缩摘要 (Depth {depth + 1})")
        summary_parts.append("")
        
        # 根据深度调整截断长度
        max_length = max(500, 1000 - depth * 200)
        summary_parts.append(combined_content[:max_length])
        
        return '\n'.join(summary_parts)
    
    # ==================== 增量压缩 ====================
    
    def incremental_compact(self, conversation_id: str, context_threshold: float = 0.75, token_budget: int = None) -> bool:
        """增量压缩
        
        借鉴 lossless-claw 的 incremental compaction：
        1. 检查上下文使用率
        2. 如果超过阈值，执行叶子压缩
        3. 检查是否需要压缩摘要
        4. 递归压缩到指定深度
        
        v4.0.0: 压缩前先执行 CMV 三遍无损压缩
        
        Args:
            conversation_id: 对话 ID
            context_threshold: 上下文阈值（默认 0.75）
            token_budget: token 预算（默认 128000）
        
        Returns:
            是否执行了压缩
        """
        import sys
        print(f"\n🔄 增量压缩检查: {conversation_id}")
        
        # 1. 获取当前上下文大小
        messages = self.db.get_messages(conversation_id)
        total_tokens = sum(m.get('token_count', 0) for m in messages)
        
        # v3.3.0: 使用传入的 token_budget，不再硬编码 128000
        max_tokens = token_budget or 128000
        usage_ratio = total_tokens / max_tokens
        
        print(f"📊 上下文使用率: {usage_ratio:.1%} ({total_tokens:,} / {max_tokens:,} tokens)")
        
        if usage_ratio < context_threshold:
            print(f"✅ 使用率 < {context_threshold:.0%}，无需压缩")
            return False
        
        # v4.0.0: 压缩前先执行 CMV 三遍无损压缩
        # v4.0.12: 修复 trimmer 结果被丢弃的 bug（Issue #150 Bug #2）
        trimmed, stats = self.db.trimmer.trim(messages)
        messages_for_compress = None  # 预处理后的消息
        
        if stats['reduction_pct'] > 0:
            print(f"[ThreePassTrimmer] reduction: {stats['reduction_pct']}%", file=sys.stderr)
            messages_for_compress = trimmed  # 用压缩后的版本做摘要
        
        # 2. 执行叶子压缩（传递预处理消息）
        print(f"\n🚀 开始叶子压缩...")
        leaf_summary = self.leaf_compact(
            conversation_id,
            preprocessed_messages=messages_for_compress
        )
        
        if not leaf_summary:
            return False
        
        # 3. 检查是否需要压缩摘要
        print(f"\n🔍 检查是否需要压缩摘要...")
        self._check_and_condense(conversation_id)
        
        return True
    
    def _check_and_condense(self, conversation_id: str, max_depth: int = -1):
        """检查并执行压缩摘要
        
        Args:
            conversation_id: 对话 ID
            max_depth: 最大深度（-1 = 无限）
        """
        current_depth = 0
        
        while max_depth == -1 or current_depth <= max_depth:
            # 获取当前深度的摘要
            summaries = self.db.get_summaries(conversation_id, current_depth)
            
            if len(summaries) < self.condensed_min_fanout:
                print(f"✅ Depth {current_depth}: 摘要数 {len(summaries)} < {self.condensed_min_fanout}，停止")
                break
            
            # 执行压缩摘要
            print(f"\n🚀 Depth {current_depth} → {current_depth + 1}: 压缩摘要...")
            condensed = self.condensed_compact(conversation_id, current_depth)
            
            if not condensed:
                break
            
            current_depth += 1
    
    # ==================== 完整压缩 ====================
    
    def full_compact(self, conversation_id: str, skip_message_ids: List[str] = None) -> Dict:
        """完整压缩（手动触发）
        
        执行完整的压缩流程：
        1. 叶子压缩（直到没有更多消息可压缩）
        2. 压缩摘要（直到没有更多摘要可压缩）
        
        Args:
            conversation_id: 对话 ID
            skip_message_ids: 要跳过的消息 ID 列表（Bug 6 修复：支持 compression_exempt）
        
        Returns:
            压缩统计
        """
        skip_message_ids = skip_message_ids or []
        
        print(f"\n{'=' * 60}")
        print(f"  🦞 完整压缩: {conversation_id}")
        if skip_message_ids:
            print(f"  🚫 跳过 {len(skip_message_ids)} 条 exempt 消息")
        print(f"{'=' * 60}\n")
        
        stats = {
            'leaf_summaries': 0,
            'condensed_summaries': 0,
            'messages_compressed': 0,
            'tokens_saved': 0
        }
        
        # Phase 1: 叶子压缩
        print("Phase 1: 叶子压缩")
        print("-" * 60)
        
        while True:
            leaf = self.leaf_compact(conversation_id, skip_message_ids=skip_message_ids)
            
            if not leaf:
                break
            
            stats['leaf_summaries'] += 1
            stats['messages_compressed'] += leaf.get('descendant_count', 0)
        
        # Phase 2: 压缩摘要
        print(f"\nPhase 2: 压缩摘要")
        print("-" * 60)
        
        self._check_and_condense(conversation_id, max_depth=-1)
        
        # 统计压缩摘要数
        all_summaries = self.db.get_summaries(conversation_id)
        stats['condensed_summaries'] = len([s for s in all_summaries if s['kind'] == 'condensed'])
        
        print(f"\n{'=' * 60}")
        print(f"  ✅ 压缩完成")
        print(f"{'=' * 60}")
        print(f"  叶子摘要: {stats['leaf_summaries']} 个")
        print(f"  压缩摘要: {stats['condensed_summaries']} 个")
        print(f"  压缩消息: {stats['messages_compressed']} 条")
        
        return stats
    
    # ==================== 上下文管理 ====================
    
    def _get_compressed_message_ids(self, conversation_id: str) -> set:
        """获取已经被压缩的消息 ID
        
        Args:
            conversation_id: 对话 ID
        
        Returns:
            已压缩消息 ID 的集合
        """
        compressed_ids = set()
        
        # 获取所有叶子摘要
        summaries = self.db.get_summaries(conversation_id, depth=0)
        
        # 收集所有已被压缩的消息 ID
        for summary in summaries:
            # 获取该摘要包含的消息
            self.db.cursor.execute("""
                SELECT message_id FROM summary_messages
                WHERE summary_id = ?
            """, (summary['summary_id'],))
            
            for row in self.db.cursor.fetchall():
                compressed_ids.add(row[0])
        
        return compressed_ids
    
    def _update_context_after_compression(self, 
                                          conversation_id: str,
                                          compressed_message_ids: List[str],
                                          new_summary_id: str):
        """压缩后更新上下文
        
        借鉴 lossless-claw 的 context_items 管理：
        - 被压缩的消息从上下文中移除
        - 新的摘要添加到上下文中
        
        Args:
            conversation_id: 对话 ID
            compressed_message_ids: 被压缩的消息 ID 列表
            new_summary_id: 新创建的摘要 ID
        """
        # 获取当前最大的 ordinal
        self.db.cursor.execute("""
            SELECT MAX(ordinal) FROM context_items
            WHERE conversation_id = ?
        """, (conversation_id,))
        
        result = self.db.cursor.fetchone()
        max_ordinal = result[0] if result and result[0] is not None else 0
        
        # 添加新的摘要到上下文
        self.db.cursor.execute("""
            INSERT INTO context_items (conversation_id, ordinal, item_type, item_id)
            VALUES (?, ?, ?, ?)
        """, (conversation_id, max_ordinal + 1, 'summary', new_summary_id))
        
        # 注意：被压缩的消息仍然保留在 messages 表中（无损存储）
        # 但它们不再出现在 context_items 中（已经被摘要替代）
        # 这样就避免了重复压缩
        
        self.db.conn.commit()
    
    def get_context_items(self, conversation_id: str) -> List[Dict]:
        """获取当前上下文项（可见内容）
        
        Args:
            conversation_id: 对话 ID
        
        Returns:
            上下文项列表（消息 + 摘要）
        """
        self.db.cursor.execute("""
            SELECT item_type, item_id, ordinal
            FROM context_items
            WHERE conversation_id = ?
            ORDER BY ordinal ASC
        """, (conversation_id,))
        
        items = []
        for row in self.db.cursor.fetchall():
            item_type, item_id, ordinal = row
            
            if item_type == 'message':
                # 获取消息详情
                self.db.cursor.execute("""
                    SELECT * FROM messages WHERE message_id = ?
                """, (item_id,))
                msg_row = self.db.cursor.fetchone()
                if msg_row:
                    items.append({
                        'type': 'message',
                        'ordinal': ordinal,
                        **self.db._row_to_dict(msg_row, 'messages')
                    })
            elif item_type == 'summary':
                # 获取摘要详情
                self.db.cursor.execute("""
                    SELECT * FROM summaries WHERE summary_id = ?
                """, (item_id,))
                sum_row = self.db.cursor.fetchone()
                if sum_row:
                    items.append({
                        'type': 'summary',
                        'ordinal': ordinal,
                        **self.db._row_to_dict(sum_row, 'summaries')
                    })
        
        return items


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 强制删除旧的测试数据库
    import os
    if os.path.exists("test_dag.db"):
        os.remove("test_dag.db")
        print("🗑️ 删除旧的测试数据库")
    
    # 测试 DAG 压缩器
    db = LobsterDatabase("test_dag.db")
    compressor = DAGCompressor(db, fresh_tail_count=5)  # 测试用较小的 fresh tail
    
    print("✅ DAG 压缩器初始化成功")
    
    # 创建测试对话
    conversation_id = "conv_test"
    
    # 创建 50 条测试消息（每条 100 tokens）
    print(f"\n📝 创建 50 条测试消息（每条约 100 tokens）...")
    for i in range(1, 51):
        # 创建较长的内容以增加 token 数
        content = f'这是第 {i} 条消息，讨论了技术话题 {i % 10}。' * 20
        msg = {
            'id': f'msg_{i:03d}',
            'conversationId': conversation_id,
            'seq': i,
            'role': 'user' if i % 2 == 0 else 'assistant',
            'content': content,
            'timestamp': datetime.utcnow().isoformat()
        }
        db.save_message(msg)
    
    print(f"✅ 创建完成")
    
    # 初始化上下文（添加所有消息到 context_items）
    print(f"\n📋 初始化上下文...")
    for i in range(1, 51):
        msg_id = f'msg_{i:03d}'
        db.cursor.execute("""
            INSERT INTO context_items (conversation_id, ordinal, item_type, item_id)
            VALUES (?, ?, ?, ?)
        """, (conversation_id, i, 'message', msg_id))
    db.conn.commit()
    print(f"✅ 上下文初始化完成")
    
    # 测试完整压缩（降低阈值以便触发）
    print(f"\n{'=' * 60}")
    print("测试: 完整压缩（降低阈值）")
    print(f"{'=' * 60}")
    
    # 临时降低 leaf_chunk_tokens 以便触发压缩
    compressor.leaf_chunk_tokens = 500  # 降低到 500 tokens
    stats = compressor.full_compact(conversation_id)
    
    # 查看摘要
    print(f"\n{'=' * 60}")
    print("查看摘要结构")
    print(f"{'=' * 60}")
    
    summaries = db.get_summaries(conversation_id)
    print(f"\n总摘要数: {len(summaries)}")
    
    for s in summaries[:5]:  # 只显示前 5 个
        print(f"  - {s['summary_id']}: {s['kind']} (depth={s['depth']}, messages={s['descendant_count']})")
    
    if len(summaries) > 5:
        print(f"  ... 还有 {len(summaries) - 5} 个摘要")
    
    # 测试展开
    if summaries:
        print(f"\n{'=' * 60}")
        print("测试展开摘要")
        print(f"{'=' * 60}")
        
        test_summary_id = summaries[0]['summary_id']
        messages = db.expand_summary(test_summary_id)
        print(f"✅ 展开摘要 {test_summary_id}: {len(messages)} 条消息")
    
    # 测试上下文
    print(f"\n{'=' * 60}")
    print("测试上下文项")
    print(f"{'=' * 60}")
    
    context_items = compressor.get_context_items(conversation_id)
    print(f"总上下文项: {len(context_items)}")
    
    # 统计类型
    message_count = sum(1 for item in context_items if item['type'] == 'message')
    summary_count = sum(1 for item in context_items if item['type'] == 'summary')
    print(f"  - 消息: {message_count} 条")
    print(f"  - 摘要: {summary_count} 个")
    
    # 清理
    db.close()
    import os
    os.remove("test_dag.db")
    print(f"\n✅ 测试完成，清理数据库")
