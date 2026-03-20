#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic Memory Layer - 语义记忆层

独立于 DAG 的稳定知识库，存储从对话中提炼的持久性事实。
每轮对话的上下文组装时，Notes 层始终注入在最前面。

Author: LobsterPress Team
Version: v4.0.13
"""

import json
import hashlib
from typing import List, Dict, Optional
from datetime import datetime

# v3.2.1: 使用集中的 prompt 模块
from prompts import build_note_extraction_prompt


class SemanticMemory:
    """语义记忆层：管理从对话中提炼的稳定事实"""
    
    def __init__(self, db):
        self.db = db
        self._ensure_schema()
    
    def _ensure_schema(self):
        """创建 notes 表（如不存在）"""
        self.db.cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                note_id         TEXT UNIQUE NOT NULL,
                conversation_id TEXT NOT NULL,
                category        TEXT NOT NULL,
                content         TEXT NOT NULL,
                confidence      REAL DEFAULT 1.0,
                source_msg_ids  TEXT,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                superseded_by   TEXT,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(conversation_id)
            );
        """)
        self.db.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_conversation
            ON notes(conversation_id, category);
        """)
        self.db.conn.commit()
    
    def extract_and_store(
        self,
        conversation_id: str,
        messages: List[Dict],
        llm_client,
        source_msg_ids: List[str] = None
    ) -> List[str]:
        """
        调用 LLM 从消息中提取语义知识，存入 notes 表。
        通常在每次 DAG 叶子压缩后调用（一次 LLM 调用，顺带提取）。
        
        v3.2.1: 使用优化的 prompt 模板
        
        Args:
            conversation_id: 对话 ID
            messages: 消息列表
            llm_client: LLM 客户端（与 dag_compressor.py 相同）
            source_msg_ids: 源消息 ID 列表
        
        Returns:
            新创建的 note_id 列表
        """
        # v3.2.1: 使用优化的 prompt 构建
        prompt = build_note_extraction_prompt(messages)
        
        try:
            # v3.2.1: 统一使用 generate() 方法
            response = llm_client.generate(prompt, temperature=0.5, max_tokens=800)
            notes_data = json.loads(response.strip())
        except Exception as e:
            print(f'⚠️ Note 提取失败: {e}')
            return []
        
        created_ids = []
        for note in notes_data:
            if not note.get('content') or not note.get('category'):
                continue
            note_id = self._save_note(
                conversation_id=conversation_id,
                category=note['category'],
                content=note['content'],
                source_msg_ids=source_msg_ids or []
            )
            if note_id:
                created_ids.append(note_id)
        
        return created_ids
    
    def _save_note(
        self,
        conversation_id: str,
        category: str,
        content: str,
        confidence: float = 1.0,
        source_msg_ids: List[str] = None
    ) -> Optional[str]:
        """保存单条 note，去重（相同内容不重复插入）"""
        # 简单去重：content 完全相同则跳过
        self.db.cursor.execute("""
            SELECT note_id FROM notes
            WHERE conversation_id = ? AND content = ? AND superseded_by IS NULL
        """, (conversation_id, content))
        if self.db.cursor.fetchone():
            return None  # 已存在
        
        note_id = 'note_' + hashlib.sha256(
            (conversation_id + content).encode()
        ).hexdigest()[:16]
        now = datetime.utcnow().isoformat()
        
        self.db.cursor.execute("""
            INSERT INTO notes
            (note_id, conversation_id, category, content, confidence,
             source_msg_ids, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            note_id, conversation_id, category, content, confidence,
            json.dumps(source_msg_ids or []), now, now
        ))
        self.db.conn.commit()
        return note_id
    
    def get_active_notes(
        self,
        conversation_id: str,
        categories: List[str] = None,
        max_tokens: int = 500
    ) -> List[Dict]:
        """
        获取当前生效的 notes（未被 supersede 的）。
        上下文组装时调用，注入上下文头部。
        
        Args:
            conversation_id: 对话 ID
            categories: 过滤类别（None 表示全部）
            max_tokens: 最大 token 数（默认 500）
        
        Returns:
            note 字典列表
        """
        if categories:
            placeholders = ','.join('?' * len(categories))
            self.db.cursor.execute(f"""
                SELECT * FROM notes
                WHERE conversation_id = ?
                  AND category IN ({placeholders})
                  AND superseded_by IS NULL
                ORDER BY category, created_at
            """, [conversation_id] + categories)
        else:
            self.db.cursor.execute("""
                SELECT * FROM notes
                WHERE conversation_id = ? AND superseded_by IS NULL
                ORDER BY category, created_at
            """, (conversation_id,))
        
        notes = self._rows_to_notes()
        
        # token 预算控制
        result = []
        used = 0
        for note in notes:
            token_cost = len(note['content']) // 4 + 10
            if used + token_cost > max_tokens:
                break
            result.append(note)
            used += token_cost
        
        return result
    
    def format_for_context(self, notes: List[Dict]) -> str:
        """
        将 notes 格式化为注入上下文的文本块。
        
        输出示例：
        [背景知识]
        • [技术决策] 项目采用 React 18 + TypeScript
        • [约束条件] 部署环境为 AWS，不能使用 GCP
        • [用户偏好] 用户偏好使用 PostgreSQL
        
        Args:
            notes: note 字典列表
        
        Returns:
            格式化后的文本
        """
        if not notes:
            return ''
        
        CATEGORY_LABELS = {
            'decision':   '技术决策',
            'constraint': '约束条件',
            'preference': '用户偏好',
            'fact':       '已知事实',
        }
        
        lines = ['[背景知识]']
        for note in notes:
            label = CATEGORY_LABELS.get(note['category'], note['category'])
            lines.append(f'• [{label}] {note["content"]}')
        
        return '\n'.join(lines)
    
    def _format_messages(self, messages: List[Dict]) -> str:
        """将消息列表格式化为提示文本"""
        lines = []
        for msg in messages[:20]:  # 最多传 20 条
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:200]  # 截断长消息
            lines.append(f'{role}: {content}')
        return '\n'.join(lines)
    
    def _rows_to_notes(self) -> List[Dict]:
        """将 cursor 结果转为字典列表"""
        cols = [d[0] for d in self.db.cursor.description]
        return [dict(zip(cols, row)) for row in self.db.cursor.fetchall()]
