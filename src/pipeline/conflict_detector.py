#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Conflict Detector - 记忆矛盾检测

使用本地轻量 NLI 模型（零 API 成本）检测新消息是否与
已有 notes 产生矛盾，并触发「记忆重巩固」更新 notes 表。

推荐模型：cross-encoder/nli-deberta-v3-small（~90MB，本地运行）
备选方案：规则 + 关键词（零依赖，精度较低）

Author: LobsterPress Team
Version: v3.0.0
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConflictResult:
    """矛盾检测结果"""
    old_note_id: str
    old_content: str
    old_category: str  # 旧 note 的类别，用于继承
    new_claim: str
    conflict_score: float  # 0.0 - 1.0，越高越矛盾


class ConflictDetector:
    """
    记忆矛盾检测器。
    
    优先使用 NLI 模型（高精度），
    不可用时自动降级为规则检测（零依赖）。
    """
    
    def __init__(self, use_nli: bool = True, nli_threshold: float = 0.85):
        self.nli_threshold = nli_threshold
        self.nli_model = None
        
        if use_nli:
            try:
                from sentence_transformers import CrossEncoder
                self.nli_model = CrossEncoder(
                    'cross-encoder/nli-deberta-v3-small',
                    max_length=256
                )
                print('✅ ConflictDetector: 使用 NLI 模型（高精度）')
            except ImportError:
                print('⚠️ ConflictDetector: sentence-transformers 未安装，降级为规则检测')
    
    def detect(
        self,
        new_message: Dict,
        existing_notes: List[Dict]
    ) -> List[ConflictResult]:
        """
        检测新消息是否与已有 notes 矛盾。
        
        Args:
            new_message: 新到达的消息
            existing_notes: 当前生效的 notes 列表
        
        Returns:
            矛盾结果列表（通常为空，偶尔 1-2 个）
        """
        content = new_message.get('content', '')
        if not content or len(content) < 10:
            return []
        
        conflicts = []
        for note in existing_notes:
            conflict = self._check_pair(note['content'], content)
            if conflict and conflict.conflict_score >= self.nli_threshold:
                conflict.old_note_id = note['note_id']
                conflict.old_category = note.get('category', 'decision')  # 继承旧 category
                conflicts.append(conflict)
        
        return conflicts
    
    def _check_pair(
        self, premise: str, hypothesis: str
    ) -> Optional[ConflictResult]:
        """检查单对 (premise, hypothesis) 是否矛盾"""
        if self.nli_model:
            return self._check_with_nli(premise, hypothesis)
        else:
            return self._check_with_rules(premise, hypothesis)
    
    def _check_with_nli(
        self, premise: str, hypothesis: str
    ) -> Optional[ConflictResult]:
        """使用 NLI 模型检测矛盾（entailment / neutral / contradiction）"""
        try:
            # CrossEncoder 输出 [entailment, neutral, contradiction] 分数
            scores = self.nli_model.predict(
                [(premise, hypothesis)],
                apply_softmax=True
            )[0]
            contradiction_score = float(scores[2])
            
            if contradiction_score >= self.nli_threshold:
                return ConflictResult(
                    old_note_id='',
                    old_content=premise,
                    old_category='',  # 由 detect() 填充
                    new_claim=hypothesis,
                    conflict_score=contradiction_score
                )
        except Exception as e:
            print(f'⚠️ NLI 检测失败: {e}')
        return None
    
    def _check_with_rules(
        self, premise: str, hypothesis: str
    ) -> Optional[ConflictResult]:
        """
        规则降级检测：检查否定词 + 关键词共现。
        精度较低，但零依赖。
        """
        NEGATION_PATTERNS = [
            r'不(用|要|采用|使用|选择)',
            r'改(用|为|成)',
            r'放弃|弃用|替换|迁移到',
            r"don't use|switch to|replace|migrate to|no longer",
        ]
        
        # 提取 premise 中的关键词（技术名词、版本号等）
        tech_words = re.findall(
            r'[A-Z][a-zA-Z]+|[a-z]{3,}(?:\s+\d+\.\d+)?|[\u4e00-\u9fff]{2,4}',
            premise
        )
        
        # 检查 hypothesis 是否包含「否定 + 关键词」
        for word in tech_words:
            for neg in NEGATION_PATTERNS:
                pattern = neg + r'[^\n]{0,20}' + re.escape(word)
                if re.search(pattern, hypothesis, re.IGNORECASE):
                    return ConflictResult(
                        old_note_id='',
                        old_content=premise,
                        old_category='',  # 由 detect() 填充
                        new_claim=hypothesis,
                        conflict_score=0.9  # 规则命中，给高分
                    )
        return None
    
    def reconcile(
        self,
        semantic_memory,    # SemanticMemory 实例
        conflicts: List[ConflictResult],
        new_message: Dict,
        conversation_id: str,
        llm_client=None     # 可选：用于高质量 note 提炼
    ):
        """
        执行记忆重巩固（Memory Reconsolidation）：
        1. 将旧 note 标记为 superseded_by 新 note
        2. 创建反映新信息的 note（优先使用 LLM 提炼）
        3. 旧 note 不删除（保留溯源链）
        
        Args:
            semantic_memory: SemanticMemory 实例
            conflicts: 矛盾检测结果列表
            new_message: 新消息
            conversation_id: 对话 ID
            llm_client: 可选的 LLM 客户端（用于高质量提炼）
        """
        for conflict in conflicts:
            # 优先使用 LLM 提炼（高质量）
            if llm_client:
                note_ids = semantic_memory.extract_and_store(
                    conversation_id=conversation_id,
                    messages=[new_message],
                    llm_client=llm_client,
                    source_msg_ids=[new_message.get('id', '')]
                )
                new_note_id = note_ids[0] if note_ids else None
            else:
                # 降级：直接截取消息内容
                new_note_id = semantic_memory._save_note(
                    conversation_id=conversation_id,
                    category=conflict.old_category,  # 继承旧 category
                    content=f'[更新] {conflict.new_claim[:200]}',
                    confidence=0.7,  # 降级时信心度降低
                    source_msg_ids=[new_message.get('id', '')]
                )
            
            if new_note_id:
                # 标记旧 note 被取代（不删除，保留历史）
                semantic_memory.db.cursor.execute("""
                    UPDATE notes
                    SET superseded_by = ?, updated_at = ?
                    WHERE note_id = ?
                """, (new_note_id, 
                       datetime.utcnow().isoformat(),
                       conflict.old_note_id))
                semantic_memory.db.conn.commit()
                
                print(f'🔄 记忆重巩固: [{conflict.old_content[:40]}...] '
                      f'→ [{conflict.new_claim[:40]}...]')
