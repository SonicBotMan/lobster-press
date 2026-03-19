#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ThreePassTrimmer — 基于 CMV 论文(arXiv:2602.22402)的三遍无损压缩引擎

论文: Contextual Memory Virtualisation: DAG-Based State Management for LLM Agents
arXiv: https://arxiv.org/abs/2602.22402
"""

import re
import json
import hashlib
from typing import List, Dict, Tuple


class ThreePassTrimmer:
    """
    三遍结构性无损压缩器。
    
    无损原则：user/assistant 消息内容永远不被修改或删除。
    只压缩：tool 输出、system boilerplate、重复内容。
    """
    
    # Pass 3 折叠的 boilerplate 模式（可扩展）
    BOILERPLATE_PATTERNS = [
        r'\[MEMORY REMINDER\].*?(?=\n|$)',
        r'<system-reminder>.*?</system-reminder>',
        r'Current Date:.*?(?=\n|$)',
    ]
    
    def trim(self, messages: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        对消息列表执行三遍压缩，返回压缩后的消息和压缩统计。
        
        Args:
            messages: 原始消息列表，每条消息格式与 save_message 输入一致
        
        Returns:
            (trimmed_messages, stats)
            stats = {
                'original_tokens': int,
                'trimmed_tokens': int,
                'reduction_pct': float,
                'pass1_saved': int,
                'pass2_saved': int,
                'pass3_saved': int,
            }
        """
        original_tokens = sum(self._estimate_tokens(self._msg_to_text(m)) for m in messages)
        
        after_p1, p1_saved = self._pass1_strip_mechanical_bloat(messages)
        after_p2, p2_saved = self._pass2_dedup_tool_results(after_p1)
        after_p3, p3_saved = self._pass3_fold_boilerplate(after_p2)
        
        trimmed_tokens = sum(self._estimate_tokens(self._msg_to_text(m)) for m in after_p3)
        reduction_pct = (1 - trimmed_tokens / original_tokens) * 100 if original_tokens > 0 else 0.0
        
        return after_p3, {
            'original_tokens': original_tokens,
            'trimmed_tokens': trimmed_tokens,
            'reduction_pct': round(reduction_pct, 2),
            'pass1_saved': p1_saved,
            'pass2_saved': p2_saved,
            'pass3_saved': p3_saved,
        }
    
    # ── Pass 1: 剥离机械性 Bloat ──────────────────────────────────────────────
    
    def _pass1_strip_mechanical_bloat(self, messages: List[Dict]) -> Tuple[List[Dict], int]:
        """
        Pass 1: 保留 user/assistant 全部内容，压缩 tool 输出中的机械性 bloat。
        
        压缩策略：
        - base64 编码块（图片/文件） → '[base64 data: {mime_type}, {original_bytes} bytes]'
        - JSON 超过 500 字符的 tool 输出 → 提取前 200 字符摘要行
        - 所有 user/assistant 内容：原样保留，绝不修改
        """
        result = []
        saved = 0
        
        for msg in messages:
            role = msg.get('role', '')
            
            # user / assistant 消息：原样保留（无损原则）
            if role in ('user', 'assistant'):
                result.append(msg)
                continue
            
            # tool / system 消息：尝试压缩
            content = msg.get('content', '')
            original_len = len(content) if isinstance(content, str) else len(json.dumps(content))
            
            compressed_content = self._compress_tool_content(content)
            compressed_len = len(compressed_content) if isinstance(compressed_content, str) else len(json.dumps(compressed_content))
            
            saved += max(0, original_len - compressed_len)
            result.append({**msg, 'content': compressed_content, '_pass1_compressed': True})
        
        return result, saved
    
    def _compress_tool_content(self, content):
        """压缩单条 tool 内容"""
        if isinstance(content, str):
            # 检测 base64
            if self._is_base64_blob(content):
                return f'[base64 data, {len(content)} chars]'
            # 超长 JSON → 摘要
            if len(content) > 500 and self._looks_like_json(content):
                return content[:200] + f'... [truncated {len(content)-200} chars]'
            return content
        
        if isinstance(content, list):
            return [self._compress_tool_block(block) for block in content]
        
        return content
    
    def _compress_tool_block(self, block: Dict) -> Dict:
        """压缩内容块中的 base64 和超长 JSON"""
        if not isinstance(block, dict):
            return block
        
        block_type = block.get('type', '')
        
        if block_type == 'image':
            src = block.get('source', {})
            if src.get('type') == 'base64':
                data = src.get('data', '')
                return {
                    'type': 'image_ref',
                    'mime_type': src.get('media_type', 'unknown'),
                    'original_bytes': len(data) * 3 // 4,  # base64 解码估算
                    '_trimmed': True
                }
        
        if block_type == 'tool_result':
            inner = block.get('content', '')
            if isinstance(inner, str) and len(inner) > 500:
                return {**block, 'content': inner[:200] + f'... [+{len(inner)-200} chars]', '_trimmed': True}
        
        return block
    
    # ── Pass 2: 重复 Tool 结果去重 ────────────────────────────────────────────
    
    def _pass2_dedup_tool_results(self, messages: List[Dict]) -> Tuple[List[Dict], int]:
        """
        Pass 2: 对连续相同（或高度相似）的 tool 结果去重。
        
        策略：对每个 tool_use_id 或 (tool_name, content_hash) 组合，
        只保留最后一次出现，删除之前的重复项。
        user/assistant 消息不参与去重。
        """
        result = []
        saved = 0
        # key: (tool_name, content_hash_prefix) → last_index
        seen: Dict[str, int] = {}
        
        # 第一遍：记录每个 key 最后出现的位置
        for i, msg in enumerate(messages):
            if msg.get('role') not in ('user', 'assistant'):
                key = self._tool_result_key(msg)
                if key:
                    seen[key] = i
        
        # 第二遍：跳过非最后出现的重复 tool 结果
        for i, msg in enumerate(messages):
            if msg.get('role') not in ('user', 'assistant'):
                key = self._tool_result_key(msg)
                if key and seen.get(key) != i:
                    # 这不是最后一次，跳过
                    saved += self._estimate_tokens(self._msg_to_text(msg))
                    continue
            result.append(msg)
        
        return result, saved
    
    def _tool_result_key(self, msg: Dict):
        """生成 tool 结果的去重 key"""
        content = self._msg_to_text(msg)
        if not content or len(content) < 10:
            return None
        tool_name = msg.get('name') or msg.get('tool_name') or msg.get('role', 'tool')
        content_hash = hashlib.md5(content[:300].encode()).hexdigest()[:8]
        return f"{tool_name}:{content_hash}"
    
    # ── Pass 3: 折叠 System Boilerplate ──────────────────────────────────────
    
    def _pass3_fold_boilerplate(self, messages: List[Dict]) -> Tuple[List[Dict], int]:
        """
        Pass 3: 将重复出现的 system reminders 折叠为单次出现。
        
        例如：每轮都注入的 [MEMORY REMINDER] 或 <system-reminder>，
        只保留最后一次，其余替换为 '[boilerplate folded]'。
        """
        result = []
        saved = 0
        seen_boilerplate = set()
        
        # 倒序处理：保留最后出现的 boilerplate
        reversed_msgs = list(reversed(messages))
        reversed_result = []
        
        for msg in reversed_msgs:
            if msg.get('role') != 'system':
                reversed_result.append(msg)
                continue
            
            content = self._msg_to_text(msg)
            bp_key = self._boilerplate_key(content)
            
            if bp_key:
                if bp_key in seen_boilerplate:
                    # 已有更新的版本，折叠这条
                    saved += self._estimate_tokens(content)
                    reversed_result.append({**msg, 'content': '[boilerplate folded]', '_pass3_folded': True})
                else:
                    seen_boilerplate.add(bp_key)
                    reversed_result.append(msg)
            else:
                reversed_result.append(msg)
        
        return list(reversed(reversed_result)), saved
    
    def _boilerplate_key(self, content: str):
        """识别内容是否为已知 boilerplate，返回其 key"""
        for pattern in self.BOILERPLATE_PATTERNS:
            if re.search(pattern, content, re.DOTALL | re.IGNORECASE):
                # 用模式本身作为 key（同类 boilerplate 归为一组）
                return pattern[:30]
        return None
    
    # ── 工具方法 ──────────────────────────────────────────────────────────────
    
    def _msg_to_text(self, msg: Dict) -> str:
        content = msg.get('content', '')
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    parts.append(block.get('text') or block.get('content') or '')
            return ' '.join(parts)
        return str(content)
    
    def _is_base64_blob(self, s: str) -> bool:
        if len(s) < 100:
            return False
        b64_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
        sample = s[:200].replace('\n', '')
        return len(sample) > 0 and sum(c in b64_chars for c in sample) / len(sample) > 0.95
    
    def _looks_like_json(self, s: str) -> bool:
        stripped = s.strip()
        return (stripped.startswith('{') and stripped.endswith('}')) or \
               (stripped.startswith('[') and stripped.endswith(']'))
    
    def _estimate_tokens(self, text: str) -> int:
        chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        return int((len(text) - chinese) / 4 + chinese / 1.5)
