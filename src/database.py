#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress Database - 无损存储层
借鉴 lossless-claw 的数据库设计

Author: LobsterPress Team
Version: v4.0.10
"""

import sqlite3
import json
import hashlib
import uuid
import math
import sys
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime

# v4.0.0: 导入 ThreePassTrimmer（兼容多种导入场景）
try:
    from .three_pass_trimmer import ThreePassTrimmer
except ImportError:
    # 当直接运行或从父目录导入时
    from three_pass_trimmer import ThreePassTrimmer


class LobsterDatabase:
    """LobsterPress 数据库 - 无损存储层"""

    def __init__(self, db_path: str = "lobster_press.db", namespace: str = "default"):
        """初始化数据库

        v3.6.0: 新增 namespace 参数（Issue #127 模块四）
        v4.0.0: 新增 trimmer（CMV 三遍压缩）

        Args:
            db_path: 数据库文件路径
            namespace: 记忆命名空间（用于多 Agent/项目隔离）
        """
        self.db_path = db_path
        self.namespace = namespace  # v3.6.0 新增
        self.trimmer = ThreePassTrimmer()  # v4.0.0 新增
        self.conn = None
        self.cursor = None
        self._init_database()
    
    def _init_database(self):
        """初始化数据库结构 - 借鉴 lossless-claw"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # 消息表（永久保存）
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                conversation_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                token_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                metadata TEXT,
                -- v2.5.0 新增字段
                msg_type TEXT DEFAULT 'unknown',
                tfidf_score REAL DEFAULT 0.0,
                structural_bonus REAL DEFAULT 0.0,
                compression_exempt INTEGER DEFAULT 0,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            );
        """)
        
        # 摘要表（DAG 结构）
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                summary_id TEXT UNIQUE NOT NULL,
                conversation_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                depth INTEGER NOT NULL,
                content TEXT NOT NULL,
                token_count INTEGER DEFAULT 0,
                earliest_at TEXT,
                latest_at TEXT,
                descendant_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            );
        """)
        
        # 对话表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT
            );
        """)
        
        # 摘要-消息关系（叶子摘要）
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS summary_messages (
                summary_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                PRIMARY KEY (summary_id, message_id),
                FOREIGN KEY (summary_id) REFERENCES summaries(summary_id),
                FOREIGN KEY (message_id) REFERENCES messages(message_id)
            );
        """)
        
        # 摘要-摘要关系（压缩摘要）
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS summary_parents (
                summary_id TEXT NOT NULL,
                parent_summary_id TEXT NOT NULL,
                PRIMARY KEY (summary_id, parent_summary_id),
                FOREIGN KEY (summary_id) REFERENCES summaries(summary_id),
                FOREIGN KEY (parent_summary_id) REFERENCES summaries(summary_id)
            );
        """)
        
        # 上下文项（当前可见内容）
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_items (
                conversation_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                PRIMARY KEY (conversation_id, ordinal),
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            );
        """)
        
        # FTS5 全文搜索 - 消息
        self.cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts 
            USING fts5(
                message_id,
                content,
                content='messages',
                content_rowid='id'
            );
        """)
        
        # FTS5 全文搜索 - 摘要
        self.cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS summaries_fts 
            USING fts5(
                summary_id,
                content,
                content='summaries',
                content_rowid='id'
            );
        """)
        
        # 大文件表（借鉴 lossless-claw）
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS large_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT UNIQUE NOT NULL,
                file_name TEXT,
                mime_type TEXT,
                byte_size INTEGER,
                content TEXT,
                exploration_summary TEXT,
                storage_path TEXT,
                created_at TEXT NOT NULL
            );
        """)
        
        # 创建索引
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id, seq);
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_summaries_conversation 
            ON summaries(conversation_id, depth);
        """)
        
        self.conn.commit()
        
        # v2.5.0 迁移
        self.migrate_v25()

        # v2.6.0 迁移
        self.migrate_v26()

        # v3.6.0 迁移
        self.migrate_v30()  # 三层记忆模型
        self.migrate_v31()  # 命名空间隔离
        self.migrate_v32()  # 记忆纠错系统
        self.migrate_v40()  # v4.0.0 R³Mem 可逆三层压缩
    
    def migrate_v25(self):
        """v2.5.0 schema 迁移
        
        为已有数据库添加新字段（向前兼容）
        """
        migrations = [
            "ALTER TABLE messages ADD COLUMN msg_type TEXT DEFAULT 'unknown'",
            "ALTER TABLE messages ADD COLUMN tfidf_score REAL DEFAULT 0.0",
            "ALTER TABLE messages ADD COLUMN structural_bonus REAL DEFAULT 0.0",
            "ALTER TABLE messages ADD COLUMN compression_exempt INTEGER DEFAULT 0",
        ]
        
        for sql in migrations:
            try:
                self.cursor.execute(sql)
            except sqlite3.OperationalError:
                # 字段已存在，跳过
                pass
        
        self.conn.commit()
    
    def migrate_v26(self):
        """v2.6.0 schema 迁移：支持遗忘曲线动态评分
        
        新增字段：
        - last_accessed_at: 最后访问时间（记忆巩固）
        - access_count: 访问次数
        - stability: 稳定性参数（半衰期天数）
        """
        migrations = [
            "ALTER TABLE messages ADD COLUMN last_accessed_at TEXT",
            "ALTER TABLE messages ADD COLUMN access_count INTEGER DEFAULT 0",
            "ALTER TABLE messages ADD COLUMN stability REAL DEFAULT 14.0",
        ]
        
        for sql in migrations:
            try:
                self.cursor.execute(sql)
            except sqlite3.OperationalError:
                # 字段已存在，跳过
                pass
        
        self.conn.commit()

    def migrate_v32(self):
        """v3.6.0 schema 迁移：记忆纠错系统（Issue #127 模块三）

        新增表：
        - corrections: 记忆纠错记录
        """
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                correction_id TEXT UNIQUE NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                correction_type TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                reason TEXT,
                created_at TEXT NOT NULL,
                applied_at TEXT
            )
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_corrections_target 
            ON corrections(target_type, target_id)
        """)
        
        self.conn.commit()

    def migrate_v40(self):
        """v4.0.0 schema 迁移：R³Mem 可逆三层压缩
        
        v4.0.2 修订：移除 v3.x 已处理的字段（memory_tier, namespace），
        只保留 v4.0.0 真正新增的表和字段（Issue #136 Bug 6）
        
        新增表：
        - entities: 实体追踪（人名、文件名、概念等）
        - entity_mentions: 实体-消息关联
        
        新增字段：
        - summaries.r3_layer: R³Mem 层级（1=document, 2=paragraph, 3=entity）
        
        Ref: arXiv:2502.15957 — R³Mem: Bridging Memory Retention and Retrieval
        """
        migrations = [
            # 实体表：追踪对话中出现的关键实体
            """
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT UNIQUE NOT NULL,
                conversation_id TEXT NOT NULL,
                namespace TEXT DEFAULT 'default',
                entity_type TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                mention_count INTEGER DEFAULT 1,
                summary TEXT
            );
            """,
            # 实体-消息关联表
            """
            CREATE TABLE IF NOT EXISTS entity_mentions (
                entity_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                PRIMARY KEY (entity_id, message_id)
            );
            """,
            # summaries 表增加 r3_layer 字段（仅 v4.0.0 新增）
            "ALTER TABLE summaries ADD COLUMN r3_layer INTEGER DEFAULT 1",
            # 创建索引
            "CREATE INDEX IF NOT EXISTS idx_entities_conversation ON entities(conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(entity_name)",
            # 注意：memory_tier 已由 migrate_v30 处理，namespace 已由 migrate_v31 处理
        ]
        
        for sql in migrations:
            try:
                self.cursor.execute(sql)
            except sqlite3.OperationalError:
                # 字段或索引已存在，忽略
                pass
        
        self.conn.commit()

    def migrate_v30(self):
        """v3.6.0 schema 迁移：三层记忆模型（Issue #127 模块一）

        新增字段：
        - memory_tier: 记忆层级（working/episodic/semantic）
        """
        migrations = [
            "ALTER TABLE summaries ADD COLUMN memory_tier TEXT DEFAULT 'episodic'",
            "ALTER TABLE messages ADD COLUMN memory_tier TEXT DEFAULT 'working'",
        ]

        for sql in migrations:
            try:
                self.cursor.execute(sql)
            except sqlite3.OperationalError:
                # 字段已存在，跳过
                pass

        self.conn.commit()

    def migrate_v31(self):
        """v3.6.0 schema 迁移：命名空间隔离（Issue #127 模块四）

        新增字段：
        - namespace: 记忆命名空间（用于多 Agent/项目隔离）

        新增索引：
        - idx_conversations_namespace: 加速按命名空间查询
        """
        migrations = [
            "ALTER TABLE conversations ADD COLUMN namespace TEXT DEFAULT 'default'",
            "CREATE INDEX IF NOT EXISTS idx_conversations_namespace ON conversations(namespace)",
        ]

        for sql in migrations:
            try:
                self.cursor.execute(sql)
            except sqlite3.OperationalError:
                # 字段或索引已存在，跳过
                pass

        self.conn.commit()

    # ==================== 消息操作 ====================
    
    def save_message(self, message: Dict) -> str:
        """保存消息（永久存储）
        
        Phase 3 (Issue #115): 使用事务确保消息和 FTS 索引的原子性
        
        Args:
            message: 消息对象（v2.5.0 支持 msg_type, tfidf_score, compression_exempt）
        
        Returns:
            message_id
        """
        message_id = message.get('id') or self._generate_id('msg')
        conversation_id = message.get('conversationId')
        seq = message.get('seq', 0)
        role = message.get('role', 'user')
        content = self._extract_content(message)
        token_count = self._estimate_tokens(content)
        created_at = message.get('timestamp') or datetime.utcnow().isoformat()
        metadata = json.dumps(message, ensure_ascii=False)
        
        # v2.5.0 新字段
        msg_type = message.get('msg_type', 'unknown')
        tfidf_score = message.get('tfidf_score', 0.0)
        structural_bonus = message.get('structural_bonus', 0.0)
        compression_exempt = 1 if message.get('compression_exempt', False) else 0
        
        # Phase 3: 使用事务确保原子性
        with self.conn:
            # Bug 1 修复：查询是否已存在（区分 INSERT vs REPLACE）
            self.cursor.execute(
                "SELECT id FROM messages WHERE message_id = ?", (message_id,)
            )
            existing = self.cursor.fetchone()
            old_rowid = existing[0] if existing else None
            
            # 执行 UPSERT
            self.cursor.execute("""
                INSERT OR REPLACE INTO messages 
                (message_id, conversation_id, seq, role, content, token_count, created_at, metadata,
                 msg_type, tfidf_score, structural_bonus, compression_exempt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (message_id, conversation_id, seq, role, content, token_count, created_at, metadata,
                  msg_type, tfidf_score, structural_bonus, compression_exempt))
            
            new_rowid = self.cursor.lastrowid
            
            # 维护 FTS5 索引：先删旧，再插新
            if old_rowid is not None:
                self.cursor.execute(
                    "DELETE FROM messages_fts WHERE rowid = ?", (old_rowid,)
                )
            self.cursor.execute(
                "INSERT INTO messages_fts (rowid, message_id, content) VALUES (?, ?, ?)",
                (new_rowid, message_id, content)
            )
        
        return message_id
    
    def get_messages(self, conversation_id: str, limit: int = None) -> List[Dict]:
        """获取对话的所有消息
        
        Args:
            conversation_id: 对话 ID
            limit: 最大消息数
        
        Returns:
            消息列表
        """
        query = """
            SELECT * FROM messages 
            WHERE conversation_id = ? 
            ORDER BY seq ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        self.cursor.execute(query, (conversation_id,))
        rows = self.cursor.fetchall()
        
        return [self._row_to_dict(row, 'messages') for row in rows]
    
    def get_messages_with_dynamic_score(
        self, conversation_id: str, current_time: datetime = None
    ) -> List[Dict]:
        """
        v2.6.0：获取消息列表，附带实时计算的动态重要性分数（遗忘曲线）
        
        Args:
            conversation_id: 对话 ID
            current_time: 当前时间（用于测试）
        
        Returns:
            带 dynamic_score 字段的消息列表
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        messages = self.get_messages(conversation_id)
        for msg in messages:
            msg['dynamic_score'] = self._compute_retention(msg, current_time)
        
        return messages
    
    def touch_message(self, message_id: str):
        """
        v4.0.0: 更新访问记录 + C-HLR+ 间隔重复稳定性增长
        
        稳定性增长从固定 *1.3 改为对数增长：
        new_stability = old_stability * (1 + 0.5 / sqrt(access_count + 1))
        首次访问时增幅最大（+50%），随后收益递减（避免无限增长）
        
        Ref: arXiv:2004.11327 — Adaptive Forgetting Curves
        
        Args:
            message_id: 消息 ID
        """
        now = datetime.utcnow().isoformat()
        self.cursor.execute("""
            UPDATE messages
            SET last_accessed_at = ?,
                access_count = COALESCE(access_count, 0) + 1,
                stability = COALESCE(stability, 14.0) * (
                    1.0 + 0.5 / SQRT(COALESCE(access_count, 0) + 1.0)
                )
            WHERE message_id = ?
        """, (now, message_id))
        self.conn.commit()
    
    def _compute_retention(self, msg: Dict, current_time: datetime) -> float:
        """
        v4.0.0: C-HLR+ 自适应遗忘曲线
        
        半衰期公式（复杂度驱动）：
            h = base_h * (1 + α * complexity) * spaced_repetition_bonus
        
        保留概率：
            R(t) = base_score * 2^(-delta_t / h)
        
        complexity = 词汇丰富度(0-1) × 句子数量因子 × 结构深度因子
        spaced_repetition_bonus = 1 + 0.5 * log(1 + access_count)
        
        对比原实现：
        - 原版：R(t) = base_score * e^(-t / stability)，stability 为固定常数
        - v4.0：半衰期随内容复杂度动态调整，指数底数从 e 改为 2（更符合记忆研究惯例）
        
        Ref: arXiv:2004.11327 — Adaptive Forgetting Curves for Spaced Repetition
        
        Args:
            msg: 消息字典
            current_time: 当前时间
        
        Returns:
            动态保留率（0.0 - base_score）
        """
        # ── 基础半衰期（天），按消息类型，与 v2.6 保持一致 ──
        BASE_HALF_LIFE = {
            'decision': 90.0,
            'config':   120.0,
            'code':     60.0,
            'error':    30.0,
            'chitchat': 3.0,
            'question': 7.0,
            'fact':     14.0,
            'unknown':  14.0,
        }
        
        # ── Step 1: 基础参数 ──
        base_score = msg.get('tfidf_score', 1.0) + msg.get('structural_bonus', 0.0)
        if base_score <= 0:
            base_score = 1.0
        
        msg_type = msg.get('msg_type', 'unknown')
        base_h = BASE_HALF_LIFE.get(msg_type, 14.0)
        
        # ── Step 2: 内容复杂度因子（C-HLR+ 核心创新）──
        content = msg.get('content', '')
        if not isinstance(content, str):
            content = str(content)
        
        complexity = self._compute_complexity(content)  # 返回 [0.0, 3.0]
        alpha = 0.5  # 复杂度权重系数（论文推荐值）
        
        # ── Step 3: 间隔重复加成（已被 touch_message 动态更新）──
        access_count = msg.get('access_count', 0) or 0
        spaced_bonus = 1.0 + 0.5 * math.log1p(access_count)
        
        # ── Step 4: 自适应半衰期 ──
        adaptive_h = base_h * (1.0 + alpha * complexity) * spaced_bonus
        
        # ── Step 5: 时间衰减（以 2 为底，符合记忆研究惯例）──
        ref_time_str = msg.get('last_accessed_at') or msg.get('created_at', '')
        try:
            ref_time = datetime.fromisoformat(ref_time_str)
            delta_days = max((current_time - ref_time).total_seconds() / 86400.0, 0.0)
        except Exception:
            delta_days = 0.0
        
        # compression_exempt 消息不衰减
        if msg.get('compression_exempt'):
            return base_score
        
        retention = base_score * math.pow(2.0, -delta_days / adaptive_h)
        return retention
    
    def _compute_complexity(self, content: str) -> float:
        """
        v4.0.0: 计算文本复杂度分数（C-HLR+ 辅助方法）
        
        三个维度的加权组合：
        1. 词汇丰富度 = unique_words / total_words（type-token ratio）
        2. 长度因子 = min(len(content) / 500, 1.0)（归一化到 [0,1]）
        3. 结构深度 = 是否含代码块/列表/嵌套结构
        
        Returns:
            complexity in [0.0, 3.0]
        
        Ref: arXiv:2004.11327
        """
        if not content or len(content) < 20:
            return 0.0
        
        # 维度1：词汇丰富度（TTR）
        words = content.lower().split()
        if len(words) < 5:
            ttr = 0.5
        else:
            ttr = min(len(set(words)) / len(words), 1.0)
        
        # 维度2：长度因子
        length_factor = min(len(content) / 500.0, 1.0)
        
        # 维度3：结构深度
        structure_score = 0.0
        if '```' in content or '    ' in content:   # 代码块
            structure_score += 0.5
        if any(content.count(marker) > 2 for marker in ['- ', '* ', '1. ']):  # 列表
            structure_score += 0.3
        if content.count('\n') > 5:  # 多段落
            structure_score += 0.2
        
        complexity = ttr + length_factor + min(structure_score, 1.0)
        return min(complexity, 3.0)  # 上限 3.0
    
    def remove_messages_from_context(self, conversation_id: str, message_ids: List[str]) -> int:
        """从 context_items 中移除指定消息（light 去重策略使用）
        
        注意：消息本体在 messages 表中永久保留（无损原则），只从上下文视图中移除。
        
        Args:
            conversation_id: 对话 ID
            message_ids: 要移除的消息 ID 列表
        
        Returns:
            实际移除的条数
        """
        if not message_ids:
            return 0
        
        placeholders = ','.join('?' * len(message_ids))
        self.cursor.execute(f"""
            DELETE FROM context_items
            WHERE conversation_id = ?
              AND item_type = 'message'
              AND item_id IN ({placeholders})
        """, [conversation_id] + message_ids)
        
        removed_count = self.cursor.rowcount
        self.conn.commit()
        return removed_count
    
    def get_exempt_message_ids(self, conversation_id: str) -> List[str]:
        """获取对话中所有 compression_exempt=1 的消息 ID
        
        Args:
            conversation_id: 对话 ID
        
        Returns:
            exempt 消息 ID 列表
        """
        self.cursor.execute(
            "SELECT message_id FROM messages WHERE conversation_id = ? AND compression_exempt = 1",
            (conversation_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]
    
    # ==================== 摘要操作 ====================
    
    def save_summary(self, summary: Dict) -> str:
        """保存摘要（DAG 节点）
        
        Args:
            summary: 摘要对象
        
        Returns:
            summary_id
        """
        summary_id = summary.get('summary_id') or self._generate_id('sum')
        conversation_id = summary['conversation_id']
        kind = summary['kind']  # 'leaf' or 'condensed'
        depth = summary['depth']
        content = summary['content']
        token_count = self._estimate_tokens(content)
        earliest_at = summary.get('earliest_at')
        latest_at = summary.get('latest_at')
        descendant_count = summary.get('descendant_count', 0)
        created_at = datetime.utcnow().isoformat()
        r3_layer = summary.get('r3_layer', 1)  # v4.0.0: R³Mem 层级
        memory_tier = summary.get('memory_tier', 'episodic')  # v3.6.0: 记忆层级
        
        # v4.0.3: 使用事务保护，确保 FTS 与主表写入原子性（Issue #137 New Bug 2）
        with self.conn:
            # Bug 1 修复：查询是否已存在
            self.cursor.execute(
                "SELECT id FROM summaries WHERE summary_id = ?", (summary_id,)
            )
            existing = self.cursor.fetchone()
            old_rowid = existing[0] if existing else None
            
            # 执行 UPSERT（v4.0.2: 补充 r3_layer 和 memory_tier）
            self.cursor.execute("""
                INSERT OR REPLACE INTO summaries 
                (summary_id, conversation_id, kind, depth, content, token_count, 
                 earliest_at, latest_at, descendant_count, created_at,
                 r3_layer, memory_tier)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (summary_id, conversation_id, kind, depth, content, token_count,
                  earliest_at, latest_at, descendant_count, created_at,
                  r3_layer, memory_tier))
            
            new_rowid = self.cursor.lastrowid
            
            # 维护 FTS5 索引：先删旧，再插新
            if old_rowid is not None:
                self.cursor.execute(
                    "DELETE FROM summaries_fts WHERE rowid = ?", (old_rowid,)
                )
            self.cursor.execute(
                "INSERT INTO summaries_fts (rowid, summary_id, content) VALUES (?, ?, ?)",
                (new_rowid, summary_id, content)
            )
            
            # 保存关系
            if kind == 'leaf':
                # 叶子摘要：关联消息
                for msg_id in summary.get('source_messages', []):
                    self.cursor.execute("""
                        INSERT OR IGNORE INTO summary_messages (summary_id, message_id)
                        VALUES (?, ?)
                    """, (summary_id, msg_id))
            else:
                # 压缩摘要：关联父摘要
                for parent_id in summary.get('parent_summaries', []):
                    self.cursor.execute("""
                        INSERT OR IGNORE INTO summary_parents (summary_id, parent_summary_id)
                        VALUES (?, ?)
                    """, (summary_id, parent_id))
        
        return summary_id
    
    def get_summaries(self, conversation_id: str, depth: int = None) -> List[Dict]:
        """获取对话的摘要
        
        Args:
            conversation_id: 对话 ID
            depth: 摘要深度（None = 所有深度）
        
        Returns:
            摘要列表
        """
        if depth is not None:
            self.cursor.execute("""
                SELECT * FROM summaries 
                WHERE conversation_id = ? AND depth = ?
                ORDER BY created_at ASC
            """, (conversation_id, depth))
        else:
            self.cursor.execute("""
                SELECT * FROM summaries 
                WHERE conversation_id = ?
                ORDER BY depth ASC, created_at ASC
            """, (conversation_id,))
        
        rows = self.cursor.fetchall()
        return [self._row_to_dict(row, 'summaries') for row in rows]
    
    # ==================== 搜索操作 ====================

    def search_messages(self, query: str, conversation_id: str = None, limit: int = 50,
                       cross_namespace: bool = False) -> List[Dict]:
        """搜索消息 - 借鉴 lcm_grep

        v3.6.0: 新增 cross_namespace 参数（Issue #127 模块四）

        Args:
            query: 搜索查询
            conversation_id: 可选，限定搜索范围的会话 ID（v3.5.0 新增）
            limit: 最大结果数
            cross_namespace: 是否跨命名空间搜索（默认 False）

        Returns:
            匹配的消息列表
        """
        if conversation_id:
            # v3.6.0: 按 conversation_id 和 namespace 过滤
            self.cursor.execute("""
                SELECT m.*, snippet(messages_fts, 1, '>>>', '<<<', '...', 10) as snippet
                FROM messages m
                JOIN messages_fts fts ON m.id = fts.rowid
                JOIN conversations c ON m.conversation_id = c.conversation_id
                WHERE messages_fts MATCH ?
                  AND m.conversation_id = ?
                  AND (? OR c.namespace = ?)
                ORDER BY rank
                LIMIT ?
            """, (query, conversation_id, cross_namespace, self.namespace, limit))
        else:
            # v3.6.0: 按 namespace 过滤
            self.cursor.execute("""
                SELECT m.*, snippet(messages_fts, 1, '>>>', '<<<', '...', 10) as snippet
                FROM messages m
                JOIN messages_fts fts ON m.id = fts.rowid
                JOIN conversations c ON m.conversation_id = c.conversation_id
                WHERE messages_fts MATCH ?
                  AND (? OR c.namespace = ?)
                ORDER BY rank
                LIMIT ?
            """, (query, cross_namespace, self.namespace, limit))

        rows = self.cursor.fetchall()
        return [self._row_to_dict(row, 'messages') for row in rows]

    def search_summaries(self, query: str, conversation_id: str = None, limit: int = 50,
                        cross_namespace: bool = False) -> List[Dict]:
        """搜索摘要 - 借鉴 lcm_grep

        v3.6.0: 新增 cross_namespace 参数（Issue #127 模块四）

        Args:
            query: 搜索查询
            conversation_id: 可选，限定搜索范围的会话 ID（v3.5.0 新增）
            limit: 最大结果数
            cross_namespace: 是否跨命名空间搜索（默认 False）

        Returns:
            匹配的摘要列表
        """
        if conversation_id:
            # v3.6.0: 按 conversation_id 和 namespace 过滤
            self.cursor.execute("""
                SELECT s.*, snippet(summaries_fts, 1, '>>>', '<<<', '...', 10) as snippet
                FROM summaries s
                JOIN summaries_fts fts ON s.id = fts.rowid
                JOIN conversations c ON s.conversation_id = c.conversation_id
                WHERE summaries_fts MATCH ?
                  AND s.conversation_id = ?
                  AND (? OR c.namespace = ?)
                ORDER BY rank
                LIMIT ?
            """, (query, conversation_id, cross_namespace, self.namespace, limit))
        else:
            # v3.6.0: 按 namespace 过滤
            self.cursor.execute("""
                SELECT s.*, snippet(summaries_fts, 1, '>>>', '<<<', '...', 10) as snippet
                FROM summaries s
                JOIN summaries_fts fts ON s.id = fts.rowid
                JOIN conversations c ON s.conversation_id = c.conversation_id
                WHERE summaries_fts MATCH ?
                  AND (? OR c.namespace = ?)
                ORDER BY rank
                LIMIT ?
            """, (query, cross_namespace, self.namespace, limit))

        rows = self.cursor.fetchall()
        return [self._row_to_dict(row, 'summaries') for row in rows]

    def get_context_by_tier(
        self,
        conversation_id: str,
        tiers: list = None
    ) -> dict:
        """v3.6.0: 按记忆层级获取上下文内容（Issue #127 模块一）

        Args:
            conversation_id: 对话 ID
            tiers: 要获取的层级列表（默认 ['working', 'episodic', 'semantic']）

        Returns:
            {
                'working': [最近 N 条原始消息],
                'episodic': [DAG 叶节点摘要],
                'semantic': [condensed 高层摘要]
            }
        """
        tiers = tiers or ['working', 'episodic', 'semantic']
        result = {}

        if 'working' in tiers:
            # 最近 20 条未被压缩的消息（working 层）
            working = self._execute_fetch_all(
                """SELECT * FROM messages
                   WHERE conversation_id = ? AND memory_tier = 'working'
                   ORDER BY seq DESC LIMIT 20""",
                (conversation_id,),
                table='messages'
            )
            result['working'] = working

        if 'episodic' in tiers:
            # DAG 叶节点摘要（episodic 层）
            episodic = self._execute_fetch_all(
                """SELECT * FROM summaries
                   WHERE conversation_id = ? AND memory_tier = 'episodic'
                   ORDER BY created_at DESC LIMIT 10""",
                (conversation_id,),
                table='summaries'
            )
            result['episodic'] = episodic

        if 'semantic' in tiers:
            # condensed 高层摘要（semantic 层）
            semantic = self._execute_fetch_all(
                """SELECT * FROM summaries
                   WHERE conversation_id = ? AND memory_tier = 'semantic'
                   ORDER BY created_at DESC LIMIT 5""",
                (conversation_id,),
                table='summaries'
            )
            result['semantic'] = semantic

        return result

    def apply_correction(
        self,
        target_type: str,
        target_id: str,
        correction_type: str,
        old_value: str,
        new_value: str,
        reason: str = None
    ) -> dict:
        """v3.6.0: 应用记忆纠错（Issue #127 模块三）

        Args:
            target_type: 目标类型（'message' 或 'summary'）
            target_id: 目标 ID
            correction_type: 纠错类型（'content', 'metadata', 'delete'）
            old_value: 旧值
            new_value: 新值
            reason: 纠错原因

        Returns:
            纠错结果
        """
        import uuid
        from datetime import datetime

        # 生成纠错 ID
        correction_id = f"corr_{uuid.uuid4().hex[:16]}"
        created_at = datetime.utcnow().isoformat()
        applied_at = datetime.utcnow().isoformat()

        # v4.0.3: 使用整体事务保护，纠错日志与修改原子提交（Issue #137 New Bug 3）
        with self.conn:
            # 记录纠错（直接带 applied_at，避免两次 UPDATE）
            self.cursor.execute("""
                INSERT INTO corrections 
                (correction_id, target_type, target_id, correction_type, old_value, new_value, reason, created_at, applied_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (correction_id, target_type, target_id, correction_type, old_value, new_value, reason, created_at, applied_at))

            # 应用纠错
            table = 'messages' if target_type == 'message' else 'summaries'
            id_field = 'message_id' if target_type == 'message' else 'summary_id'
            fts_table = 'messages_fts' if target_type == 'message' else 'summaries_fts'

            if correction_type == 'delete':
                # 先查 rowid（Issue #129 Bug 3 修复）
                self.cursor.execute(f"SELECT id FROM {table} WHERE {id_field} = ?", (target_id,))
                row = self.cursor.fetchone()
                if row:
                    # 删除 FTS 索引
                    self.cursor.execute(f"DELETE FROM {fts_table} WHERE rowid = ?", (row[0],))
                # 删除主表记录
                self.cursor.execute(f"DELETE FROM {table} WHERE {id_field} = ?", (target_id,))
            elif correction_type == 'content':
                # 先查 rowid（Issue #129 Bug 4 修复）
                self.cursor.execute(f"SELECT id FROM {table} WHERE {id_field} = ?", (target_id,))
                row = self.cursor.fetchone()
                if row:
                    old_rowid = row[0]
                    # 更新主表内容
                    self.cursor.execute(f"UPDATE {table} SET content = ? WHERE {id_field} = ?",
                                        (new_value, target_id))
                    # 同步 FTS：删除旧记录
                    self.cursor.execute(f"DELETE FROM {fts_table} WHERE rowid = ?", (old_rowid,))
                    # 插入新记录
                    self.cursor.execute(
                        f"INSERT INTO {fts_table} (rowid, {id_field}, content) VALUES (?, ?, ?)",
                        (old_rowid, target_id, new_value)
                    )
                else:
                    # 如果记录不存在，只更新主表
                    self.cursor.execute(f"UPDATE {table} SET content = ? WHERE {id_field} = ?",
                                        (new_value, target_id))
            elif correction_type == 'metadata':
                # 修改元数据
                self.cursor.execute(f"UPDATE {table} SET metadata = ? WHERE {id_field} = ?", (new_value, target_id))

        return {
            "correction_id": correction_id,
            "target_type": target_type,
            "target_id": target_id,
            "correction_type": correction_type,
            "applied_at": applied_at,
            "success": True
        }

    def upsert_entity(
        self,
        conversation_id: str,
        entity_name: str,
        entity_type: str,
        message_ids: List[str],
        namespace: str = 'default'
    ) -> str:
        """v4.0.0: 插入或更新实体记录，关联消息（R³Mem 模块四）

        由 lobster_compact 在生成摘要后调用（实体提取由 LLM 完成）。

        Args:
            conversation_id: 对话 ID
            entity_name: 实体名称（人名、文件名、概念等）
            entity_type: 实体类型（'person', 'file', 'concept', 'decision'）
            message_ids: 关联的消息 ID 列表
            namespace: 命名空间（默认 'default'）

        Returns:
            entity_id: 实体 ID

        Ref: arXiv:2502.15957 — R³Mem: Bridging Memory Retention and Retrieval
        """
        now = datetime.utcnow().isoformat()
        # v4.0.3: 改用 SHA-256[:24] 恢复幂等性（Issue #137 New Bug 1）
        # 兼顾无碰撞（96 bit）和幂等性（相同输入产生相同 ID）
        entity_id = f"ent_{hashlib.sha256((namespace + conversation_id + entity_name).encode()).hexdigest()[:24]}"
        
        # 插入或更新实体
        self.cursor.execute("""
            INSERT INTO entities
                (entity_id, conversation_id, namespace, entity_type, entity_name,
                 first_seen_at, last_seen_at, mention_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                last_seen_at = excluded.last_seen_at,
                mention_count = mention_count + ?
        """, (entity_id, conversation_id, namespace, entity_type, entity_name,
              now, now, len(message_ids), len(message_ids)))
        
        # 关联消息
        for msg_id in message_ids:
            self.cursor.execute("""
                INSERT OR IGNORE INTO entity_mentions (entity_id, message_id) VALUES (?, ?)
            """, (entity_id, msg_id))
        
        self.conn.commit()
        return entity_id

    def sweep_decayed_messages(self, conversation_id: str, days_threshold: int = 30) -> dict:
        """v3.6.1: 清理衰减消息（Issue #127 模块二 + Issue #129 Bug 1, 2）

        基于遗忘曲线，将低价值、长期未访问的消息标记为 decayed。

        ⚠️ 无损原则：消息本体永久保留，只从上下文移除并标记 tier。

        Args:
            conversation_id: 对话 ID（防止跨 namespace 误删）
            days_threshold: 未访问天数阈值（默认 30 天）

        Returns:
            清理统计
        """
        from datetime import datetime, timedelta

        cutoff_date = (datetime.utcnow() - timedelta(days=days_threshold)).isoformat()
        # v4.0.2: 增加近期消息保护期（7 天），避免误标未评分的新消息（Issue #136 Bug 5）
        protect_cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()

        # 查找符合衰减条件的消息（增加 conversation_id 过滤 + 近期保护）
        self.cursor.execute("""
            SELECT message_id, tfidf_score, access_count, last_accessed_at
            FROM messages
            WHERE conversation_id = ?
              AND COALESCE(last_accessed_at, created_at) < ?
              AND created_at < ?
              AND compression_exempt = 0
              AND tfidf_score < 0.1
            ORDER BY tfidf_score ASC, last_accessed_at ASC
            LIMIT 100
        """, (conversation_id, cutoff_date, protect_cutoff))

        candidates = [row[0] for row in self.cursor.fetchall()]

        if not candidates:
            return {
                "swept_count": 0,
                "candidates": 0,
                "days_threshold": days_threshold,
                "cutoff_date": cutoff_date
            }

        # 无损删除：只从 context_items 移除（参考 remove_messages_from_context）
        swept_count = self.remove_messages_from_context(conversation_id, candidates)

        # 标记 memory_tier 为 decayed（可查询，不物理删除）
        placeholders = ','.join('?' * len(candidates))
        self.cursor.execute(
            f"UPDATE messages SET memory_tier = 'decayed' WHERE message_id IN ({placeholders})",
            candidates
        )

        self.conn.commit()

        return {
            "swept_count": swept_count,
            "candidates": len(candidates),
            "days_threshold": days_threshold,
            "cutoff_date": cutoff_date
        }

    # ==================== 工具操作 ====================

    def describe_summary(self, summary_id: str) -> Optional[Dict]:
        """查看摘要详情 - 借鉴 lcm_describe

        v3.6.0: 修复 Issue #126 Bug 3（光标竞争）
        使用 _execute_fetch_all 避免递归调用时列名错位。

        Args:
            summary_id: 摘要 ID

        Returns:
            摘要详情
        """
        # 获取摘要（使用安全方法）
        summaries = self._execute_fetch_all(
            "SELECT * FROM summaries WHERE summary_id = ?",
            (summary_id,),
            table='summaries'
        )

        if not summaries:
            return None

        summary = summaries[0]

        # 获取子节点（使用安全方法）
        if summary['kind'] == 'leaf':
            children = self._execute_fetch_all(
                """SELECT m.* FROM messages m
                   JOIN summary_messages sm ON m.message_id = sm.message_id
                   WHERE sm.summary_id = ?
                   ORDER BY m.seq ASC""",
                (summary_id,),
                table='messages'
            )
        else:
            children = self._execute_fetch_all(
                """SELECT s.* FROM summaries s
                   JOIN summary_parents sp ON s.summary_id = sp.parent_summary_id
                   WHERE sp.summary_id = ?
                   ORDER BY s.created_at ASC""",
                (summary_id,),
                table='summaries'
            )

        summary['children'] = children
        summary['children_count'] = len(children)

        return summary
    
    def expand_summary(
        self,
        summary_id: str,
        target_layer: int = 1,
        entity_filter: str = None
    ) -> List[Dict]:
        """v4.0.0: R³Mem 可逆三层展开

        target_layer 含义（对应 R³Mem 论文）：
            1 = Document-Level：返回 summaries（当前行为，保持兼容）
            2 = Paragraph-Level：返回原始 messages
            3 = Entity-Level：返回与特定实体相关的 messages

        entity_filter: 实体名称（仅 target_layer=3 时生效）

        Ref: arXiv:2502.15957 — R³Mem: Bridging Memory Retention and Retrieval

        Args:
            summary_id: 摘要 ID
            target_layer: 目标展开层级（1, 2, 3）
            entity_filter: 实体过滤（仅 layer=3）

        Returns:
            消息或摘要列表
        """
        summary = self.describe_summary(summary_id)
        if not summary:
            return []

        # Layer 1: document-level（返回子摘要列表，原有行为）
        if target_layer == 1:
            if summary['kind'] == 'leaf':
                return summary['children']  # 返回源消息
            return summary['children']      # 返回子摘要（原逻辑）

        # Layer 2: paragraph-level（递归展开到原始消息）
        if target_layer == 2:
            if summary['kind'] == 'leaf':
                return summary['children']
            all_messages = []
            for child in summary['children']:
                child_id = child.get('summary_id') or child.get('message_id')
                if child.get('summary_id'):
                    all_messages.extend(self.expand_summary(child_id, target_layer=2))
                else:
                    all_messages.append(child)
            return all_messages

        # Layer 3: entity-level（按实体过滤）
        if target_layer == 3:
            all_messages = self.expand_summary(summary_id, target_layer=2)
            if not entity_filter:
                return all_messages
            # 过滤与实体相关的消息
            self.cursor.execute("""
                SELECT em.message_id FROM entity_mentions em
                JOIN entities e ON em.entity_id = e.entity_id
                WHERE e.entity_name LIKE ?
            """, (f'%{entity_filter}%',))
            relevant_ids = {row[0] for row in self.cursor.fetchall()}
            return [m for m in all_messages if m.get('message_id') in relevant_ids]

        return []

    def get_turn_count(self, conversation_id: str) -> int:
        """v4.0.0: 获取对话的轮次数（user 消息数量）

        Args:
            conversation_id: 对话 ID

        Returns:
            轮次数
        """
        self.cursor.execute(
            "SELECT COUNT(*) FROM messages WHERE conversation_id = ? AND role = 'user'",
            (conversation_id,)
        )
        result = self.cursor.fetchone()
        return result[0] if result else 0

    # ==================== 辅助方法 ====================
    
    def _generate_id(self, prefix: str) -> str:
        """生成唯一 ID
        
        Args:
            prefix: ID 前缀（'msg', 'sum' 等）
        
        Returns:
            唯一 ID
        """
        # Bug 4 修复：使用 uuid4 避免批量调用时的碰撞
        return f"{prefix}_{uuid.uuid4().hex[:16]}"
    
    def _extract_content(self, message: Dict) -> str:
        """提取消息内容
        
        Args:
            message: 消息对象
        
        Returns:
            文本内容
        """
        content = message.get('content', [])
        
        if isinstance(content, str):
            return content
        
        if isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get('type') == 'text':
                        texts.append(block.get('text', ''))
                    elif block.get('type') == 'toolResult':
                        texts.append(f"[Tool Result: {block.get('name', 'unknown')}]")
                    elif block.get('type') == 'toolCall':
                        texts.append(f"[Tool Call: {block.get('name', 'unknown')}]")
                    elif block.get('type') == 'thinking':
                        texts.append(f"[Thinking]")
            return '\n'.join(texts)
        
        return str(content)
    
    def _estimate_tokens(self, text: str) -> int:
        """估算 token 数量
        
        Args:
            text: 文本内容
        
        Returns:
            token 数量
        """
        # 简单估算：英文 4 字符 = 1 token，中文 1.5 字符 = 1 token
        char_count = len(text)
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_chars = char_count - chinese_chars

        tokens = (english_chars / 4) + (chinese_chars / 1.5)
        return int(tokens)

    def _execute_fetch_all(self, sql: str, params: tuple = (), table: str = None) -> List[Dict]:
        """v3.6.0: 安全的查询方法，修复 Issue #126 Bug 3
        
        在 execute 后立即保存 description，避免递归调用时光标竞争。
        
        Args:
            sql: SQL 查询语句
            params: 查询参数
            table: 表名（仅用于 fallback）
        
        Returns:
            字典列表
        """
        self.cursor.execute(sql, params)
        
        # 立即保存 description（关键修复！）
        if hasattr(self.cursor, 'description') and self.cursor.description:
            columns = [desc[0] for desc in self.cursor.description]
        else:
            # Fallback: 使用硬编码列表
            if table == 'messages':
                columns = ['id', 'message_id', 'conversation_id', 'seq', 'role',
                          'content', 'token_count', 'created_at', 'metadata',
                          'msg_type', 'tfidf_score', 'structural_bonus', 'compression_exempt',
                          'last_accessed_at', 'access_count', 'stability',
                          'memory_tier']  # v3.6.1: 添加 memory_tier（Issue #129 Bug 5）
            elif table == 'summaries':
                columns = ['id', 'summary_id', 'conversation_id', 'kind', 'depth',
                          'content', 'token_count', 'earliest_at', 'latest_at',
                          'descendant_count', 'created_at',
                          'memory_tier',  # v3.6.1: 添加 memory_tier（Issue #129 Bug 5）
                          'r3_layer']     # v4.0.2: 添加 r3_layer（Issue #136 Bug 2）
            else:
                columns = []
        
        rows = self.cursor.fetchall()
        
        if not columns:
            return [dict(row) for row in rows]
        
        result = []
        for row in rows:
            item = dict(zip(columns, row))
            # 解析 JSON 字段
            if 'metadata' in item and item['metadata']:
                try:
                    item['metadata'] = json.loads(item['metadata'])
                except:
                    pass
            result.append(item)
        
        return result

    def _row_to_dict(self, row: tuple, table: str) -> Dict:
        """将数据库行转换为字典
        
        Args:
            row: 数据库行
            table: 表名（仅用于 fallback）
        
        Returns:
            字典对象
        """
        # 优先使用 cursor.description 动态获取列名（健壮方案）
        if hasattr(self.cursor, 'description') and self.cursor.description:
            columns = [desc[0] for desc in self.cursor.description]
        else:
            # Fallback: 使用硬编码列表（仅在特殊情况下）
            if table == 'messages':
                columns = ['id', 'message_id', 'conversation_id', 'seq', 'role', 
                          'content', 'token_count', 'created_at', 'metadata',
                          'msg_type', 'tfidf_score', 'structural_bonus', 'compression_exempt',
                          'last_accessed_at', 'access_count', 'stability',
                          'memory_tier']  # v3.6.1: 添加 memory_tier（Issue #129 Bug 5）
            elif table == 'summaries':
                columns = ['id', 'summary_id', 'conversation_id', 'kind', 'depth',
                          'content', 'token_count', 'earliest_at', 'latest_at',
                          'descendant_count', 'created_at',
                          'memory_tier',  # v3.6.1: 添加 memory_tier（Issue #129 Bug 5）
                          'r3_layer']     # v4.0.2: 添加 r3_layer（Issue #136 Bug 2）
            else:
                return dict(row)
        
        result = dict(zip(columns, row))
        
        # 解析 JSON 字段
        if 'metadata' in result and result['metadata']:
            try:
                result['metadata'] = json.loads(result['metadata'])
            except:
                pass
        
        return result
    
    # ==================== 辅助方法（用于测试） ====================
    
    def create_conversation(self, metadata: Dict = None) -> str:
        """创建新对话
        
        Args:
            metadata: 可选的对话元数据
        
        Returns:
            conversation_id
        """
        conversation_id = self._generate_id('conv')
        created_at = datetime.utcnow().isoformat()
        
        # v4.0.12: 添加事务保护（Issue #150 Bug #3）
        with self.conn:
            # 插入对话记录
            self.cursor.execute("""
                INSERT OR IGNORE INTO conversations (conversation_id, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?)
            """, (conversation_id, created_at, created_at, json.dumps(metadata or {})))
        
        return conversation_id
    
    def add_message(self, conversation_id: str, role: str, content: str) -> str:
        """添加消息到对话
        
        Args:
            conversation_id: 对话 ID
            role: 角色 (user/assistant)
            content: 消息内容
        
        Returns:
            message_id
        """
        message_id = self._generate_id('msg')
        
        # 使用 save_message 方法
        message = {
            'id': message_id,
            'conversationId': conversation_id,
            'role': role,
            'content': content,
            'seq': self._get_next_seq(conversation_id)
        }
        
        self.save_message(message)
        return message_id
    
    def _get_next_seq(self, conversation_id: str) -> int:
        """获取对话的下一个序号"""
        self.cursor.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        )
        result = self.cursor.fetchone()
        return result[0] if result else 0
    
    def get_conversation_stats(self, conversation_id: str) -> Optional[Dict]:
        """获取对话统计信息
        
        Args:
            conversation_id: 对话 ID
        
        Returns:
            包含 message_count, total_tokens 的字典
        """
        self.cursor.execute(
            "SELECT COUNT(*) as message_count, SUM(token_count) as total_tokens "
            "FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        )
        result = self.cursor.fetchone()
        
        if result:
            return {
                "message_count": result[0],
                "total_tokens": result[1] or 0
            }
        return None
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试数据库
    db = LobsterDatabase("test_lobster.db")
    
    print("✅ 数据库初始化成功")
    
    # 测试保存消息
    test_message = {
        'id': 'msg_test123',
        'conversationId': 'conv_test',
        'seq': 1,
        'role': 'user',
        'content': [{'type': 'text', 'text': '这是一条测试消息'}],
        'timestamp': datetime.utcnow().isoformat()
    }
    
    msg_id = db.save_message(test_message)
    print(f"✅ 保存消息: {msg_id}")
    
    # 测试搜索
    results = db.search_messages("测试")
    print(f"✅ 搜索结果: {len(results)} 条")
    
    # 测试保存摘要
    test_summary = {
        'summary_id': 'sum_test123',
        'conversation_id': 'conv_test',
        'kind': 'leaf',
        'depth': 0,
        'content': '这是测试摘要内容',
        'source_messages': ['msg_test123'],
        'earliest_at': datetime.utcnow().isoformat(),
        'latest_at': datetime.utcnow().isoformat(),
        'descendant_count': 1
    }
    
    sum_id = db.save_summary(test_summary)
    print(f"✅ 保存摘要: {sum_id}")
    
    # 测试描述摘要
    summary = db.describe_summary(sum_id)
    print(f"✅ 摘要详情: {summary['summary_id']}, 子节点: {summary['children_count']}")
    
    # 测试展开摘要
    messages = db.expand_summary(sum_id)
    print(f"✅ 展开摘要: {len(messages)} 条消息")
    
    # 关闭数据库
    db.close()
    print("✅ 数据库关闭")
    
    # 清理测试文件
    import os
    os.remove("test_lobster.db")
    print("✅ 清理测试文件")
