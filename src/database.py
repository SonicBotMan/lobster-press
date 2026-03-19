#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress Database - 无损存储层
借鉴 lossless-claw 的数据库设计

Author: LobsterPress Team
Version: v2.5.0
"""

import sqlite3
import json
import hashlib
import uuid
import math
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime


class LobsterDatabase:
    """LobsterPress 数据库 - 无损存储层"""

    def __init__(self, db_path: str = "lobster_press.db", namespace: str = "default"):
        """初始化数据库

        v3.6.0: 新增 namespace 参数（Issue #127 模块四）

        Args:
            db_path: 数据库文件路径
            namespace: 记忆命名空间（用于多 Agent/项目隔离）
        """
        self.db_path = db_path
        self.namespace = namespace  # v3.6.0 新增
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
        v2.6.0：更新消息的最后访问时间和访问次数（记忆巩固）
        
        每次 lobster_grep 命中时调用，被引用的记忆重置衰减计数器，
        稳定性提升（间隔重复效应）。
        
        Args:
            message_id: 消息 ID
        """
        now = datetime.utcnow().isoformat()
        self.cursor.execute("""
            UPDATE messages
            SET last_accessed_at = ?,
                access_count = COALESCE(access_count, 0) + 1,
                stability = COALESCE(stability, 14.0) * 1.3
            WHERE message_id = ?
        """, (now, message_id))
        self.conn.commit()
    
    def _compute_retention(self, msg: Dict, current_time: datetime) -> float:
        """
        v2.6.0：计算动态保留率（遗忘曲线）
        
        R(t) = base_score * e^(-t / stability)
        
        stability（半衰期天数）按消息类型设置：
          decision : 90 天  — 架构决策应该长期记住
          config   : 120 天 — 配置信息极少变化
          code     : 60 天  — 代码片段中期保留
          error    : 30 天  — 错误日志短期高价值
          chitchat : 3 天   — 闲聊迅速归零
          unknown  : 14 天  — 默认两周
        
        Args:
            msg: 消息字典
            current_time: 当前时间
        
        Returns:
            动态保留率（0.0 - base_score）
        """
        STABILITY_MAP = {
            'decision': 90.0,
            'config':   120.0,
            'code':     60.0,
            'error':    30.0,
            'chitchat': 3.0,
            'question': 7.0,
            'unknown':  14.0,
        }
        
        base_score = msg.get('tfidf_score', 1.0) + msg.get('structural_bonus', 0.0)
        msg_type = msg.get('msg_type', 'unknown')
        stability = msg.get('stability') or STABILITY_MAP.get(msg_type, 14.0)
        
        # 上次访问时间（优先用 last_accessed_at，其次 created_at）
        ref_time_str = msg.get('last_accessed_at') or msg.get('created_at')
        try:
            ref_time = datetime.fromisoformat(ref_time_str)
            delta_days = (current_time - ref_time).total_seconds() / 86400.0
        except Exception:
            delta_days = 0.0
        
        retention = math.exp(-max(delta_days, 0) / stability)
        
        # compression_exempt 的消息保留率不衰减
        if msg.get('compression_exempt'):
            return base_score  # 不乘衰减系数
        
        return base_score * retention
    
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
        
        # Bug 1 修复：查询是否已存在
        self.cursor.execute(
            "SELECT id FROM summaries WHERE summary_id = ?", (summary_id,)
        )
        existing = self.cursor.fetchone()
        old_rowid = existing[0] if existing else None
        
        # 执行 UPSERT
        self.cursor.execute("""
            INSERT OR REPLACE INTO summaries 
            (summary_id, conversation_id, kind, depth, content, token_count, 
             earliest_at, latest_at, descendant_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (summary_id, conversation_id, kind, depth, content, token_count,
              earliest_at, latest_at, descendant_count, created_at))
        
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
        
        self.conn.commit()
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

        # 记录纠错
        self.cursor.execute("""
            INSERT INTO corrections 
            (correction_id, target_type, target_id, correction_type, old_value, new_value, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (correction_id, target_type, target_id, correction_type, old_value, new_value, reason, created_at))

        # 应用纠错
        table = 'messages' if target_type == 'message' else 'summaries'
        id_field = 'message_id' if target_type == 'message' else 'summary_id'

        if correction_type == 'delete':
            # 删除记录
            self.cursor.execute(f"DELETE FROM {table} WHERE {id_field} = ?", (target_id,))
        elif correction_type == 'content':
            # 修改内容
            self.cursor.execute(f"UPDATE {table} SET content = ? WHERE {id_field} = ?", (new_value, target_id))
        elif correction_type == 'metadata':
            # 修改元数据
            self.cursor.execute(f"UPDATE {table} SET metadata = ? WHERE {id_field} = ?", (new_value, target_id))

        # 更新 applied_at
        applied_at = datetime.utcnow().isoformat()
        self.cursor.execute("""
            UPDATE corrections SET applied_at = ? WHERE correction_id = ?
        """, (applied_at, correction_id))

        self.conn.commit()

        return {
            "correction_id": correction_id,
            "target_type": target_type,
            "target_id": target_id,
            "correction_type": correction_type,
            "applied_at": applied_at,
            "success": True
        }

    def sweep_decayed_messages(self, days_threshold: int = 30) -> dict:
        """v3.6.0: 清理衰减消息（Issue #127 模块二）

        基于遗忘曲线，删除低价值、长期未访问的消息。

        Args:
            days_threshold: 未访问天数阈值（默认 30 天）

        Returns:
            清理统计
        """
        from datetime import datetime, timedelta

        cutoff_date = (datetime.utcnow() - timedelta(days=days_threshold)).isoformat()

        # 查找符合衰减条件的消息
        self.cursor.execute("""
            SELECT message_id, tfidf_score, access_count, last_accessed_at
            FROM messages
            WHERE last_accessed_at < ?
              AND compression_exempt = 0
              AND tfidf_score < 0.1
            ORDER BY tfidf_score ASC, last_accessed_at ASC
            LIMIT 100
        """, (cutoff_date,))

        candidates = self.cursor.fetchall()

        # 删除消息
        deleted_count = 0
        for msg in candidates:
            message_id = msg[0]
            # 从 FTS 索引删除
            self.cursor.execute("DELETE FROM messages_fts WHERE message_id = ?", (message_id,))
            # 从 summary_messages 关系删除
            self.cursor.execute("DELETE FROM summary_messages WHERE message_id = ?", (message_id,))
            # 删除消息本身
            self.cursor.execute("DELETE FROM messages WHERE message_id = ?", (message_id,))
            deleted_count += 1

        self.conn.commit()

        return {
            "deleted_count": deleted_count,
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
    
    def expand_summary(self, summary_id: str) -> List[Dict]:
        """展开摘要 - 借鉴 lcm_expand
        
        Args:
            summary_id: 摘要 ID
        
        Returns:
            原始消息列表（递归展开 DAG）
        """
        summary = self.describe_summary(summary_id)
        
        if not summary:
            return []
        
        if summary['kind'] == 'leaf':
            # 叶子摘要：直接返回源消息
            return summary['children']
        else:
            # 压缩摘要：递归展开所有子摘要
            all_messages = []
            for child in summary['children']:
                all_messages.extend(self.expand_summary(child['summary_id']))
            return all_messages
    
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
                          'last_accessed_at', 'access_count', 'stability']
            elif table == 'summaries':
                columns = ['id', 'summary_id', 'conversation_id', 'kind', 'depth',
                          'content', 'token_count', 'earliest_at', 'latest_at',
                          'descendant_count', 'created_at']
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
                          'last_accessed_at', 'access_count', 'stability']
            elif table == 'summaries':
                columns = ['id', 'summary_id', 'conversation_id', 'kind', 'depth',
                          'content', 'token_count', 'earliest_at', 'latest_at',
                          'descendant_count', 'created_at']
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
