#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress 增量压缩管理器
借鉴 lossless-claw 的增量压缩机制

Author: LobsterPress Team
Version: v3.0.0
"""

import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# 添加 database 模块
sys.path.insert(0, str(Path(__file__).parent))
from database import LobsterDatabase
from dag_compressor import DAGCompressor
from pipeline.tfidf_scorer import TFIDFScorer, EXEMPT_TYPES
from pipeline.semantic_dedup import SemanticDeduplicator

# v3.0.0: 语义记忆和矛盾检测
try:
    from semantic_memory import SemanticMemory
    from pipeline.conflict_detector import ConflictDetector
    SEMANTIC_MEMORY_AVAILABLE = True
except ImportError:
    SEMANTIC_MEMORY_AVAILABLE = False


class IncrementalCompressor:
    """增量压缩管理器
    
    借鉴 lossless-claw 的增量压缩机制：
    - 自动监控上下文使用率
    - 智能触发压缩（75% 阈值）
    - 只压缩新增内容
    - 支持多对话管理
    """
    
    def __init__(self, 
                 db: LobsterDatabase,
                 llm_client=None,  # v3.0.0: 可选的 LLM 客户端（用于 note 提取）
                 context_threshold: float = 0.75,
                 fresh_tail_count: int = 32,
                 leaf_chunk_tokens: int = 20000,
                 max_context_tokens: int = 128_000):
        """初始化增量压缩管理器
        
        Args:
            db: LobsterDatabase 实例
            context_threshold: 上下文使用率阈值（默认 75%）
            fresh_tail_count: Fresh tail 消息数（默认 32）
            leaf_chunk_tokens: 叶子压缩 token 阈值（默认 20000）
            max_context_tokens: 最大上下文 token 数（默认 128K，Claude 用户可设置为 200_000，Gemini 用户可设置为 1_000_000）
        """
        self.db = db
        self.llm_client = llm_client  # v3.0.0: LLM 客户端
        self.compressor = DAGCompressor(
            db, 
            fresh_tail_count=fresh_tail_count,
            leaf_chunk_tokens=leaf_chunk_tokens
        )
        self.context_threshold = context_threshold
        self.max_context_tokens = max_context_tokens  # 缺陷 3 修复：可配置的上下文上限
        
        # v2.5.0: 初始化 pipeline 模块
        self.tfidf_scorer = TFIDFScorer()
        self.deduplicator = SemanticDeduplicator(threshold=0.82)
        
        # v3.0.0: 初始化语义记忆和矛盾检测
        if SEMANTIC_MEMORY_AVAILABLE:
            self.semantic_memory = SemanticMemory(db)
            self.conflict_detector = ConflictDetector(use_nli=True)
            print('✅ 语义记忆层已启用（v3.0.0）')
        else:
            self.semantic_memory = None
            self.conflict_detector = None
        
        # 压缩统计
        self.stats = {
            'total_compressions': 0,
            'total_messages_compressed': 0,
            'total_tokens_saved': 0,
            'last_compression': None
        }
    
    def on_new_message(self, 
                       conversation_id: str,
                       message: Dict,
                       auto_compress: bool = True) -> Optional[Dict]:
        """新消息到达时的处理
        
        v2.5.0 更新：
        1. 使用 TFIDFScorer 评分和打标签
        2. 根据 compression_exempt 决定是否压缩
        3. 三层压缩策略：<60% 不压缩，60-75% 仅去重，>75% DAG
        
        Args:
            conversation_id: 对话 ID
            message: 新消息
            auto_compress: 是否自动压缩
        
        Returns:
            压缩统计（如果触发了压缩），否则返回 None
        """
        # v2.5.0: 评分和打标签
        scored_list = self.tfidf_scorer.score_and_tag([message])
        scored_msg = scored_list[0]
        
        # 将评分信息添加到消息中
        message['msg_type'] = scored_msg.msg_type
        message['tfidf_score'] = scored_msg.tfidf_score
        message['structural_bonus'] = scored_msg.structural_bonus
        message['compression_exempt'] = scored_msg.compression_exempt
        
        # 1. 保存消息（包含新字段）
        self.db.save_message(message)
        
        # 2. 更新上下文（支持 id 或 message_id 字段）
        msg_id = message.get('message_id') or message.get('id')
        if msg_id:
            self._add_to_context(conversation_id, msg_id)
        
        # v3.0.0: 矛盾检测（仅在语义记忆层启用时）
        if self.semantic_memory and self.conflict_detector:
            active_notes = self.semantic_memory.get_active_notes(conversation_id)
            if active_notes:
                conflicts = self.conflict_detector.detect(message, active_notes)
                if conflicts:
                    self.conflict_detector.reconcile(
                        self.semantic_memory, conflicts, message, conversation_id
                    )
        
        # 3. 检查是否需要压缩
        if auto_compress and self._should_compress(conversation_id):
            return self.compress(conversation_id)
        
        return None
    
    def compress(self, conversation_id: str) -> Dict:
        """执行压缩
        
        v2.5.0 更新：三层压缩策略
        - <60% 不压缩
        - 60-75% 仅去重
        - >75% DAG 压缩
        
        Args:
            conversation_id: 对话 ID
        
        Returns:
            压缩统计
        """
        print(f"\n{'=' * 60}")
        print(f"  🦞 增量压缩: {conversation_id}")
        print(f"{'=' * 60}\n")
        
        # 获取上下文使用率
        usage_ratio = self._get_context_usage(conversation_id)
        
        # v2.5.0: 选择压缩策略
        strategy = self._select_compression_strategy(usage_ratio)
        
        print(f"📊 上下文使用率: {usage_ratio:.1%}")
        print(f"🎯 压缩策略: {strategy}\n")
        
        stats = {
            'strategy': strategy,
            'usage_ratio': usage_ratio,
            'messages_compressed': 0,
            'tokens_saved': 0
        }
        
        if strategy == 'none':
            # <60% 不压缩
            print("✅ 上下文使用率低，无需压缩")
            return stats
        
        elif strategy == 'light':
            # 60-75% 仅去重
            messages = self.db.get_messages(conversation_id)
            
            # 重新评分所有消息
            scored_list = self.tfidf_scorer.score_and_tag(messages)
            
            # 去重
            kept, removed_ids = self.deduplicator.deduplicate(scored_list)
            
            if removed_ids:
                # Bug 3 修复：实际从上下文中移除（消息本体保留，符合无损原则）
                actual_removed = self.db.remove_messages_from_context(
                    conversation_id, removed_ids
                )
                print(f"🔄 light 去重: 从上下文移除 {actual_removed} 条重复消息（原文永久保留）")
                stats['messages_compressed'] = actual_removed
                stats['removed_ids'] = removed_ids
            else:
                print("✅ 无重复消息，上下文已是最优")
            
            return stats
        
        else:
            # >75% DAG 压缩
            # Bug 6 修复 + 设计改进：使用封装方法查询 exempt 消息
            exempt_ids = self.db.get_exempt_message_ids(conversation_id)
            
            # 执行完整压缩（跳过 exempt 消息）
            dag_stats = self.compressor.full_compact(conversation_id, skip_message_ids=exempt_ids)
            
            # 更新统计
            self.stats['total_compressions'] += 1
            self.stats['total_messages_compressed'] += dag_stats['messages_compressed']
            self.stats['total_tokens_saved'] += dag_stats.get('tokens_saved', 0)
            self.stats['last_compression'] = datetime.utcnow().isoformat()
            
            # v3.0.0: 提取语义知识（仅在 DAG 压缩后且启用语义记忆时）
            if self.semantic_memory and self.llm_client:
                messages = self.db.get_messages(conversation_id)
                source_msg_ids = [m.get('message_id') or m.get('id') for m in messages]
                
                note_ids = self.semantic_memory.extract_and_store(
                    conversation_id=conversation_id,
                    messages=messages,
                    llm_client=self.llm_client,
                    source_msg_ids=source_msg_ids
                )
                
                if note_ids:
                    dag_stats['notes_extracted'] = len(note_ids)
                    print(f"📝 语义知识提取: {len(note_ids)} 条 notes")
            
            return dag_stats
    
    def _select_compression_strategy(self, usage_ratio: float) -> str:
        """选择压缩策略（v2.5.0）
        
        Args:
            usage_ratio: 上下文使用率（0.0 - 1.0）
        
        Returns:
            压缩策略（'none', 'light', 'aggressive'）
        """
        if usage_ratio < 0.60:
            return 'none'  # <60% 不压缩
        elif usage_ratio < 0.75:
            return 'light'  # 60-75% 仅去重
        else:
            return 'aggressive'  # >75% DAG 压缩
    
    def _should_compress(self, conversation_id: str) -> bool:
        """检查是否需要压缩
        
        借鉴 lossless-claw 的智能触发机制：
        - 计算上下文使用率
        - 如果超过阈值，返回 True
        - 否则返回 False
        
        Args:
            conversation_id: 对话 ID
        
        Returns:
            是否需要压缩
        """
        # 获取上下文使用率
        usage_ratio = self._get_context_usage(conversation_id)
        
        if usage_ratio >= self.context_threshold:
            print(f"\n⚡ 触发压缩: 上下文使用率 {usage_ratio:.1%} >= {self.context_threshold:.0%}")
            return True
        
        return False
    
    def _get_context_usage(self, conversation_id: str) -> float:
        """计算上下文使用率
        
        Args:
            conversation_id: 对话 ID
        
        Returns:
            上下文使用率（0.0 - 1.0）
        """
        # 获取上下文项
        context_items = self.compressor.get_context_items(conversation_id)
        
        if not context_items:
            return 0.0
        
        # 计算总 tokens
        total_tokens = 0
        for item in context_items:
            if item['type'] == 'message':
                total_tokens += item.get('token_count', 0)
            elif item['type'] == 'summary':
                total_tokens += item.get('token_count', 0)
        
        # 缺陷 3 修复：使用配置的上下文上限（支持 Claude 200K / Gemini 1M）
        return min(total_tokens / self.max_context_tokens, 1.0)
    
    def _add_to_context(self, conversation_id: str, message_id: str):
        """添加消息到上下文
        
        Args:
            conversation_id: 对话 ID
            message_id: 消息 ID
        """
        # 获取当前最大的 ordinal
        self.db.cursor.execute("""
            SELECT MAX(ordinal) FROM context_items
            WHERE conversation_id = ?
        """, (conversation_id,))
        
        result = self.db.cursor.fetchone()
        max_ordinal = result[0] if result and result[0] is not None else 0
        
        # 添加新消息到上下文
        self.db.cursor.execute("""
            INSERT INTO context_items (conversation_id, ordinal, item_type, item_id)
            VALUES (?, ?, ?, ?)
        """, (conversation_id, max_ordinal + 1, 'message', message_id))
        
        self.db.conn.commit()
    
    def get_stats(self) -> Dict:
        """获取压缩统计
        
        Returns:
            压缩统计
        """
        return {
            **self.stats,
            'context_threshold': self.context_threshold,
            'fresh_tail_count': self.compressor.fresh_tail_count,
            'leaf_chunk_tokens': self.compressor.leaf_chunk_tokens
        }
    
    def monitor(self, conversation_id: str) -> Dict:
        """监控对话状态
        
        Args:
            conversation_id: 对话 ID
        
        Returns:
            对话状态
        """
        # 获取消息统计
        messages = self.db.get_messages(conversation_id)
        
        # 获取摘要统计
        summaries = self.db.get_summaries(conversation_id)
        
        # 获取上下文使用率
        usage_ratio = self._get_context_usage(conversation_id)
        
        # 按 depth 分组摘要
        by_depth = {}
        for summary in summaries:
            depth = summary['depth']
            if depth not in by_depth:
                by_depth[depth] = 0
            by_depth[depth] += 1
        
        return {
            'conversation_id': conversation_id,
            'total_messages': len(messages),
            'total_summaries': len(summaries),
            'context_usage': usage_ratio,
            'context_threshold': self.context_threshold,
            'needs_compression': usage_ratio >= self.context_threshold,
            'summaries_by_depth': by_depth
        }


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 强制删除旧的测试数据库
    import os
    if os.path.exists("test_incremental.db"):
        os.remove("test_incremental.db")
        print("🗑️ 删除旧的测试数据库\n")
    
    # 初始化
    db = LobsterDatabase("test_incremental.db")
    manager = IncrementalCompressor(
        db,
        context_threshold=0.001,  # 测试用，设置很低的阈值
        fresh_tail_count=5,
        leaf_chunk_tokens=500
    )
    
    print("=" * 60)
    print("  🧪 增量压缩测试")
    print("=" * 60)
    
    # 创建测试对话
    conversation_id = "conv_incremental"
    
    # 测试 1: 逐步添加消息，观察自动压缩
    print("\n📝 测试 1: 逐步添加消息（自动压缩）\n")
    
    for i in range(1, 31):
        content = f'这是第 {i} 条消息，讨论了技术话题 {i % 10}。'
        msg = {
            'id': f'msg_{i:03d}',
            'conversationId': conversation_id,
            'seq': i,
            'role': 'user' if i % 2 == 0 else 'assistant',
            'content': content * 5,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 添加消息（自动压缩）
        result = manager.on_new_message(conversation_id, msg, auto_compress=True)
        
        if result:
            print(f"\n✅ 消息 {i}: 触发压缩")
            print(f"   - 叶子摘要: {result['leaf_summaries']} 个")
            print(f"   - 压缩消息: {result['messages_compressed']} 条")
        else:
            if i % 10 == 0:
                print(f"   消息 {i}: 上下文正常")
    
    # 测试 2: 查看监控状态
    print("\n" + "=" * 60)
    print("  📊 监控状态")
    print("=" * 60)
    
    status = manager.monitor(conversation_id)
    print(f"\n对话 ID: {status['conversation_id']}")
    print(f"总消息数: {status['total_messages']}")
    print(f"总摘要数: {status['total_summaries']}")
    print(f"上下文使用率: {status['context_usage']:.2%}")
    print(f"上下文阈值: {status['context_threshold']:.0%}")
    print(f"需要压缩: {'是' if status['needs_compression'] else '否'}")
    print(f"\n摘要分布:")
    for depth, count in sorted(status['summaries_by_depth'].items()):
        print(f"  Depth {depth}: {count} 个")
    
    # 测试 3: 查看压缩统计
    print("\n" + "=" * 60)
    print("  📈 压缩统计")
    print("=" * 60)
    
    stats = manager.get_stats()
    print(f"\n总压缩次数: {stats['total_compressions']}")
    print(f"总压缩消息: {stats['total_messages_compressed']} 条")
    print(f"最后压缩时间: {stats['last_compression']}")
    
    # 清理
    db.close()
    os.remove("test_incremental.db")
    print(f"\n🗑️ 清理测试数据库")
    print(f"\n✅ 测试完成")
