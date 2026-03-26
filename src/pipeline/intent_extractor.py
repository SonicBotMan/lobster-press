"""
LobsterPress - Intent Extractor
意图提取器：从对话中提取用户意图和 assistant 结论

理论基础：
- EM-LLM：事件边界检测
- HiMem：关键信息提取
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter


@dataclass
class Intent:
    """意图"""
    intent_type: str  # 'question', 'request', 'confirmation', 'complaint'
    content: str  # 意图内容
    confidence: float  # 置信度 0-1
    source: str  # 'user' or 'assistant'
    entities: List[str] = field(default_factory=list)  # 关键实体


@dataclass
class Conclusion:
    """结论"""
    conclusion_type: str  # 'decision', 'error', 'next_step', 'result'
    content: str  # 结论内容
    confidence: float  # 置信度 0-1
    entities: List[str] = field(default_factory=list)  # 关键实体


class IntentExtractor:
    """意图提取器"""
    
    # 用户意图关键词
    USER_INTENT_PATTERNS = {
        'question': [
            r'吗[？?]',
            r'是否',
            r'有没有',
            r'怎么样',
            r'如何',
            r'什么',
            r'为什么',
            r'怎么',
        ],
        'request': [
            r'帮(我|你)',
            r'给我',
            r'看看',
            r'检查',
            r'配置',
            r'安装',
            r'修复',
            r'优化',
        ],
        'confirmation': [
            r'好的',
            r'可以',
            r'行',
            r'嗯',
            r'是的',
            r'对',
            r'记住了',
        ],
        'complaint': [
            r'还是',
            r'又',
            r'一直',
            r'重复',
            r'卡顿',
            r'问题',
        ],
    }
    
    # assistant 结论关键词
    ASSISTANT_CONCLUSION_PATTERNS = {
        'decision': [
            r'决定',
            r'选择',
            r'采用',
            r'方案',
        ],
        'error': [
            r'错误',
            r'失败',
            r'问题',
            r'bug',
            r'异常',
        ],
        'next_step': [
            r'下一步',
            r'接下来',
            r'然后',
            r'需要',
        ],
        'result': [
            r'完成',
            r'成功',
            r'已经',
            r'解决了',
            r'修复了',
        ],
    }
    
    # 实体提取模式
    ENTITY_PATTERNS = [
        r'v\d+\.\d+\.\d+',  # 版本号 v4.0.94
        r'v\d+\.\d+',  # 版本号 v4.0
        r'\d+\.\d+\.\d+',  # 版本号 4.0.94
        r'[\w\-]+\.(py|ts|js|json|md)',  # 文件名
        r'[\w\-]+/[\w\-]+',  # 路径
    ]
    
    def extract_intents(self, messages: List[Dict]) -> Dict:
        """
        从消息列表中提取意图和结论
        
        Args:
            messages: 消息列表，每个消息包含 'role' 和 'content'
        
        Returns:
            {
                'user_intents': List[Intent],
                'assistant_conclusions': List[Conclusion],
                'key_entities': List[str],
            }
        """
        user_intents = []
        assistant_conclusions = []
        all_entities = []
        
        for msg in messages:
            role = msg.get('role', '')
            content = self._extract_text_content(msg.get('content', ''))
            
            if not content:
                continue
            
            # 提取实体
            entities = self._extract_entities(content)
            all_entities.extend(entities)
            
            if role == 'user':
                # 提取用户意图
                intents = self._extract_user_intents(content, entities)
                user_intents.extend(intents)
            
            elif role == 'assistant':
                # 提取 assistant 结论
                conclusions = self._extract_assistant_conclusions(content, entities)
                assistant_conclusions.extend(conclusions)
        
        # 语义去重
        user_intents = self._deduplicate_intents(user_intents)
        assistant_conclusions = self._deduplicate_conclusions(assistant_conclusions)
        
        # 统计实体频率
        entity_counter = Counter(all_entities)
        key_entities = [entity for entity, count in entity_counter.most_common(10)]
        
        return {
            'user_intents': user_intents,
            'assistant_conclusions': assistant_conclusions,
            'key_entities': key_entities,
        }
    
    def generate_summary(self, intents_data: Dict, max_length: int = 500) -> str:
        """
        生成意图和结论的摘要
        
        Args:
            intents_data: extract_intents() 的返回值
            max_length: 最大长度
        
        Returns:
            摘要文本
        """
        lines = []
        
        # 用户意图
        user_intents = intents_data.get('user_intents', [])
        if user_intents:
            lines.append('[用户意图]')
            for intent in user_intents[:5]:  # 只显示前 5 个
                repeat_suffix = f' (重复 {intent.repeat_count} 次)' if hasattr(intent, 'repeat_count') and intent.repeat_count > 1 else ''
                lines.append(f'  • {intent.intent_type}: {intent.content[:100]}{repeat_suffix}')
        
        # assistant 结论
        assistant_conclusions = intents_data.get('assistant_conclusions', [])
        if assistant_conclusions:
            lines.append('[Assistant 结论]')
            for conclusion in assistant_conclusions[:5]:  # 只显示前 5 个
                repeat_suffix = f' (重复 {conclusion.repeat_count} 次)' if hasattr(conclusion, 'repeat_count') and conclusion.repeat_count > 1 else ''
                lines.append(f'  • {conclusion.conclusion_type}: {conclusion.content[:100]}{repeat_suffix}')
        
        # 关键实体
        key_entities = intents_data.get('key_entities', [])
        if key_entities:
            lines.append(f'[关键实体] {", ".join(key_entities[:5])}')
        
        summary = '\n'.join(lines)
        
        # 截断
        if len(summary) > max_length:
            summary = summary[:max_length] + '...'
        
        return summary
    
    def _extract_text_content(self, content) -> str:
        """从 content 中提取纯文本"""
        if isinstance(content, str):
            # 尝试解析 JSON
            try:
                data = json.loads(content)
                return self._extract_text_from_blocks(data)
            except (json.JSONDecodeError, TypeError):
                return content
        
        if isinstance(content, list):
            return self._extract_text_from_blocks(content)
        
        return ''
    
    def _extract_text_from_blocks(self, blocks) -> str:
        """从块列表中提取文本"""
        if not isinstance(blocks, list):
            return ''
        
        texts = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            
            block_type = block.get('type', '')
            
            if block_type == 'text':
                text = block.get('text', '')
                # 递归解析嵌套的 JSON
                try:
                    inner = json.loads(text)
                    texts.append(self._extract_text_from_blocks(inner))
                except (json.JSONDecodeError, TypeError):
                    texts.append(text)
            
            elif block_type == 'thinking':
                thinking = block.get('thinking', '')
                texts.append(thinking)
        
        return ' '.join(texts)
    
    def _extract_user_intents(self, content: str, entities: List[str]) -> List[Intent]:
        """提取用户意图"""
        intents = []
        
        for intent_type, patterns in self.USER_INTENT_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # 提取包含匹配的句子
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 50)
                    sentence = content[start:end].strip()
                    
                    # 计算置信度
                    confidence = 0.7 + 0.3 * (len(entities) / 5)  # 有实体则置信度更高
                    confidence = min(1.0, confidence)
                    
                    intents.append(Intent(
                        intent_type=intent_type,
                        content=sentence,
                        confidence=confidence,
                        source='user',
                        entities=entities,
                    ))
        
        # 去重
        unique_intents = []
        seen = set()
        for intent in intents:
            key = (intent.intent_type, intent.content[:50])
            if key not in seen:
                seen.add(key)
                unique_intents.append(intent)
        
        return unique_intents
    
    def _extract_assistant_conclusions(self, content: str, entities: List[str]) -> List[Conclusion]:
        """提取 assistant 结论"""
        conclusions = []
        
        for conclusion_type, patterns in self.ASSISTANT_CONCLUSION_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # 提取包含匹配的句子
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 50)
                    sentence = content[start:end].strip()
                    
                    # 计算置信度
                    confidence = 0.7 + 0.3 * (len(entities) / 5)
                    confidence = min(1.0, confidence)
                    
                    conclusions.append(Conclusion(
                        conclusion_type=conclusion_type,
                        content=sentence,
                        confidence=confidence,
                        entities=entities,
                    ))
        
        # 去重
        unique_conclusions = []
        seen = set()
        for conclusion in conclusions:
            key = (conclusion.conclusion_type, conclusion.content[:50])
            if key not in seen:
                seen.add(key)
                unique_conclusions.append(conclusion)
        
        return unique_conclusions
    
    def _extract_entities(self, content: str) -> List[str]:
        """提取关键实体"""
        entities = []
        
        for pattern in self.ENTITY_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            entities.extend(matches)
        
        # 去重
        return list(set(entities))
    
    def _deduplicate_intents(self, intents: List[Intent]) -> List[Intent]:
        """
        语义去重意图
        
        策略：
        - 相同类型 + 相似内容 → 只保留置信度最高的
        - 标注重复次数
        """
        if not intents:
            return []
        
        # 按类型分组
        grouped = {}
        for intent in intents:
            key = intent.intent_type
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(intent)
        
        # 每组内去重
        deduplicated = []
        for intent_type, group in grouped.items():
            # 按内容相似度去重
            unique = []
            for intent in group:
                # 检查是否与已有的相似
                is_duplicate = False
                for existing in unique:
                    similarity = self._calculate_similarity(intent.content, existing.content)
                    if similarity > 0.8:  # 相似度阈值
                        # 标记重复
                        if not hasattr(existing, 'repeat_count'):
                            existing.repeat_count = 1
                        existing.repeat_count += 1
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    intent.repeat_count = 1
                    unique.append(intent)
            
            deduplicated.extend(unique)
        
        # 按置信度排序
        deduplicated.sort(key=lambda x: x.confidence, reverse=True)
        
        return deduplicated
    
    def _deduplicate_conclusions(self, conclusions: List[Conclusion]) -> List[Conclusion]:
        """
        语义去重结论
        
        策略：
        - 相同类型 + 相似内容 → 只保留置信度最高的
        - 标注重复次数
        """
        if not conclusions:
            return []
        
        # 按类型分组
        grouped = {}
        for conclusion in conclusions:
            key = conclusion.conclusion_type
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(conclusion)
        
        # 每组内去重
        deduplicated = []
        for conclusion_type, group in grouped.items():
            # 按内容相似度去重
            unique = []
            for conclusion in group:
                # 检查是否与已有的相似
                is_duplicate = False
                for existing in unique:
                    similarity = self._calculate_similarity(conclusion.content, existing.content)
                    if similarity > 0.8:  # 相似度阈值
                        # 标记重复
                        if not hasattr(existing, 'repeat_count'):
                            existing.repeat_count = 1
                        existing.repeat_count += 1
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    conclusion.repeat_count = 1
                    unique.append(conclusion)
            
            deduplicated.extend(unique)
        
        # 按置信度排序
        deduplicated.sort(key=lambda x: x.confidence, reverse=True)
        
        return deduplicated
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（Jaccard 相似度）
        
        Args:
            text1: 文本1
            text2: 文本2
        
        Returns:
            相似度 0-1
        """
        # 简单的词频 Jaccard 相似度
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
