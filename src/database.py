#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress Database - 无损存储层
借鉴 lossless-claw 的数据库设计

Author: LobsterPress Team
Version: v2.0.0-alpha
"""

import sqlite3
import json
import hashlib
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime


class LobsterDatabase:
    """LobsterPress 数据库 - 无损存储层"""
    
    def __init__(self, db_path: str = "lobster_press.db"):
        """初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
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
    
    # ==================== 消息操作 ====================
    
    def save_message(self, message: Dict) -> str:
        """保存消息（永久存储）
        
        Args:
            message: 消息对象
        
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
        
        self.cursor.execute("""
            INSERT OR REPLACE INTO messages 
            (message_id, conversation_id, seq, role, content, token_count, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (message_id, conversation_id, seq, role, content, token_count, created_at, metadata))
        
        # 更新 FTS 索引
        self.cursor.execute("""
            INSERT INTO messages_fts (rowid, message_id, content)
            VALUES (last_insert_rowid(), ?, ?)
        """, (message_id, content))
        
        self.conn.commit()
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
        
        self.cursor.execute("""
            INSERT OR REPLACE INTO summaries 
            (summary_id, conversation_id, kind, depth, content, token_count, 
             earliest_at, latest_at, descendant_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (summary_id, conversation_id, kind, depth, content, token_count,
              earliest_at, latest_at, descendant_count, created_at))
        
        # 更新 FTS 索引
        self.cursor.execute("""
            INSERT INTO summaries_fts (rowid, summary_id, content)
            VALUES (last_insert_rowid(), ?, ?)
        """, (summary_id, content))
        
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
    
    def search_messages(self, query: str, limit: int = 50) -> List[Dict]:
        """搜索消息 - 借鉴 lcm_grep
        
        Args:
            query: 搜索查询
            limit: 最大结果数
        
        Returns:
            匹配的消息列表
        """
        self.cursor.execute("""
            SELECT m.*, snippet(messages_fts, 1, '>>>', '<<<', '...', 10) as snippet
            FROM messages m
            JOIN messages_fts fts ON m.id = fts.rowid
            WHERE messages_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        
        rows = self.cursor.fetchall()
        return [self._row_to_dict(row, 'messages') for row in rows]
    
    def search_summaries(self, query: str, limit: int = 50) -> List[Dict]:
        """搜索摘要 - 借鉴 lcm_grep
        
        Args:
            query: 搜索查询
            limit: 最大结果数
        
        Returns:
            匹配的摘要列表
        """
        self.cursor.execute("""
            SELECT s.*, snippet(summaries_fts, 1, '>>>', '<<<', '...', 10) as snippet
            FROM summaries s
            JOIN summaries_fts fts ON s.id = fts.rowid
            WHERE summaries_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        
        rows = self.cursor.fetchall()
        return [self._row_to_dict(row, 'summaries') for row in rows]
    
    # ==================== 工具操作 ====================
    
    def describe_summary(self, summary_id: str) -> Optional[Dict]:
        """查看摘要详情 - 借鉴 lcm_describe
        
        Args:
            summary_id: 摘要 ID
        
        Returns:
            摘要详情
        """
        # 获取摘要
        self.cursor.execute("""
            SELECT * FROM summaries WHERE summary_id = ?
        """, (summary_id,))
        row = self.cursor.fetchone()
        
        if not row:
            return None
        
        summary = self._row_to_dict(row, 'summaries')
        
        # 获取子节点
        if summary['kind'] == 'leaf':
            self.cursor.execute("""
                SELECT m.* FROM messages m
                JOIN summary_messages sm ON m.message_id = sm.message_id
                WHERE sm.summary_id = ?
                ORDER BY m.seq ASC
            """, (summary_id,))
            children = [self._row_to_dict(r, 'messages') for r in self.cursor.fetchall()]
        else:
            self.cursor.execute("""
                SELECT s.* FROM summaries s
                JOIN summary_parents sp ON s.summary_id = sp.parent_summary_id
                WHERE sp.summary_id = ?
                ORDER BY s.created_at ASC
            """, (summary_id,))
            children = [self._row_to_dict(r, 'summaries') for r in self.cursor.fetchall()]
        
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
        timestamp = datetime.utcnow().isoformat()
        random_bytes = hashlib.sha256(timestamp.encode()).hexdigest()[:16]
        return f"{prefix}_{random_bytes}"
    
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
    
    def _row_to_dict(self, row: tuple, table: str) -> Dict:
        """将数据库行转换为字典
        
        Args:
            row: 数据库行
            table: 表名
        
        Returns:
            字典对象
        """
        if table == 'messages':
            columns = ['id', 'message_id', 'conversation_id', 'seq', 'role', 
                      'content', 'token_count', 'created_at', 'metadata']
        elif table == 'summaries':
            columns = ['id', 'summary_id', 'conversation_id', 'kind', 'depth',
                      'content', 'token_count', 'earliest_at', 'latest_at',
                      'descendant_count', 'created_at']
        else:
            return dict(row)
        
        # 处理额外的字段（如 snippet）
        extra_columns = len(row) - len(columns)
        if extra_columns > 0:
            # 获取额外的列名（从 cursor description）
            if hasattr(self.cursor, 'description'):
                all_columns = [desc[0] for desc in self.cursor.description]
                columns = all_columns
        
        result = dict(zip(columns, row))
        
        # 解析 JSON 字段
        if 'metadata' in result and result['metadata']:
            try:
                result['metadata'] = json.loads(result['metadata'])
            except:
                pass
        
        return result
    
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
