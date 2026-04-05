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
        r"\[MEMORY REMINDER\].*?(?=\n|$)",
        r"<system-reminder>.*?</system-reminder>",
        r"Current Date:.*?(?=\n|$)",
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
                'pass4_saved': int,  # v4.0.95: 消息去重
            }
        """
        original_tokens = sum(
            self._estimate_tokens(self._msg_to_text(m)) for m in messages
        )

        after_p1, p1_saved = self._pass1_strip_mechanical_bloat(messages)
        after_p2, p2_saved = self._pass2_dedup_tool_results(after_p1)
        after_p3, p3_saved = self._pass3_fold_boilerplate(after_p2)

        # v4.0.95: Pass 4 - 消息去重
        after_p4, p4_saved, dedup_count = self._pass4_dedup_messages(after_p3)

        # v4.0.95: 添加 [compressed] 标记
        for msg in after_p4:
            if msg.get("_pass1_compressed") or msg.get("_pass4_dedup"):
                msg["content"] = f"[compressed] {msg.get('content', '')}"

        trimmed_tokens = sum(
            self._estimate_tokens(self._msg_to_text(m)) for m in after_p4
        )
        reduction_pct = (
            (1 - trimmed_tokens / original_tokens) * 100 if original_tokens > 0 else 0.0
        )

        return after_p4, {
            "original_tokens": original_tokens,
            "trimmed_tokens": trimmed_tokens,
            "reduction_pct": round(reduction_pct, 2),
            "pass1_saved": p1_saved,
            "pass2_saved": p2_saved,
            "pass3_saved": p3_saved,
            "pass4_saved": p4_saved,
            "dedup_count": dedup_count,  # v4.0.95: 去重消息数
        }

    # ── Pass 1: 剥离机械性 Bloat ──────────────────────────────────────────────

    def _pass1_strip_mechanical_bloat(
        self, messages: List[Dict]
    ) -> Tuple[List[Dict], int]:
        """
        Pass 1: 保留 user 全部内容，压缩 tool/assistant 输出中的机械性 bloat。

        v4.0.94: 扩展无损原则，assistant 消息中的 thinking 块和超长 JSON 也可压缩。

        压缩策略：
        - base64 编码块（图片/文件） → '[base64 data: {mime_type}, {original_bytes} bytes]'
        - JSON 超过 500 字符 → 提取前 200 字符摘要行
        - thinking 块 → 压缩为 '[thinking: {preview}...]'
        - user 内容：原样保留，绝不修改
        - assistant 内容：保留 text 块，压缩 thinking 块和超长 JSON
        """
        result = []
        saved = 0

        for msg in messages:
            role = msg.get("role", "")

            # user 消息：原样保留（无损原则）
            if role == "user":
                result.append(msg)
                continue

            # assistant 消息：压缩 thinking 块和超长 JSON
            if role == "assistant":
                content = msg.get("content", "")
                original_len = (
                    len(content)
                    if isinstance(content, str)
                    else len(json.dumps(content))
                )

                compressed_content = self._compress_assistant_content(content)
                compressed_len = (
                    len(compressed_content)
                    if isinstance(compressed_content, str)
                    else len(json.dumps(compressed_content))
                )

                saved += max(0, original_len - compressed_len)
                result.append(
                    {**msg, "content": compressed_content, "_pass1_compressed": True}
                )
                continue

            # tool / system 消息：尝试压缩
            content = msg.get("content", "")
            original_len = (
                len(content) if isinstance(content, str) else len(json.dumps(content))
            )

            compressed_content = self._compress_tool_content(content)
            compressed_len = (
                len(compressed_content)
                if isinstance(compressed_content, str)
                else len(json.dumps(compressed_content))
            )

            saved += max(0, original_len - compressed_len)
            result.append(
                {**msg, "content": compressed_content, "_pass1_compressed": True}
            )

        return result, saved

    def _compress_assistant_content(self, content):
        """v4.0.94: 压缩 assistant 消息中的 thinking 块和超长 JSON

        策略：
        - thinking 块 → 压缩为 thinking_summary
        - 超长 JSON (>500 字符) → 递归压缩嵌套结构
        - text 块 → 检查是否包含嵌套的 JSON，递归处理
        """
        if isinstance(content, str):
            # 尝试解析为 JSON
            try:
                data = json.loads(content)
                compressed = self._compress_assistant_blocks(data)
                return json.dumps(compressed, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                pass

            # 不是 JSON，超长文本 → 摘要
            if len(content) > 500:
                return content[:200] + f"... [truncated {len(content) - 200} chars]"
            return content

        if isinstance(content, list):
            compressed = self._compress_assistant_blocks(content)
            return json.dumps(compressed, ensure_ascii=False)

        return content

    def _compress_assistant_blocks(self, blocks):
        """递归压缩 assistant 消息中的块列表"""
        if not isinstance(blocks, list):
            return blocks

        result = []
        for block in blocks:
            if not isinstance(block, dict):
                result.append(block)
                continue

            block_type = block.get("type", "")

            if block_type == "thinking":
                # 压缩 thinking 块
                thinking = block.get("thinking", "")
                preview = thinking[:100] if len(thinking) > 100 else thinking
                result.append(
                    {
                        "type": "thinking_summary",
                        "preview": preview + "..." if len(thinking) > 100 else preview,
                        "original_length": len(thinking),
                        "_trimmed": True,
                    }
                )
            elif block_type == "text":
                # 检查 text 中是否包含嵌套的 JSON
                text = block.get("text", "")
                compressed_text = self._compress_nested_text(text)
                result.append({**block, "text": compressed_text})
            else:
                result.append(block)

        return result

    def _compress_nested_text(self, text: str) -> str:
        """递归压缩 text 字段中嵌套的 JSON"""
        # 尝试解析为 JSON
        try:
            data = json.loads(text)
            compressed = self._compress_assistant_blocks(data)
            return json.dumps(compressed, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            pass

        # 不是 JSON，检查是否超长
        if len(text) > 500:
            return text[:200] + f"... [truncated {len(text) - 200} chars]"
        return text

    def _compress_tool_content(self, content):
        """压缩单条 tool 内容"""
        if isinstance(content, str):
            # 检测 base64
            if self._is_base64_blob(content):
                return f"[base64 data, {len(content)} chars]"
            # 超长 JSON → 摘要
            if len(content) > 500 and self._looks_like_json(content):
                return content[:200] + f"... [truncated {len(content) - 200} chars]"
            return content

        if isinstance(content, list):
            return [self._compress_tool_block(block) for block in content]

        return content

    def _compress_tool_block(self, block: Dict) -> Dict:
        """压缩内容块中的 base64 和超长 JSON"""
        if not isinstance(block, dict):
            return block

        block_type = block.get("type", "")

        if block_type == "image":
            src = block.get("source", {})
            if src.get("type") == "base64":
                data = src.get("data", "")
                return {
                    "type": "image_ref",
                    "mime_type": src.get("media_type", "unknown"),
                    "original_bytes": len(data) * 3 // 4,  # base64 解码估算
                    "_trimmed": True,
                }

        if block_type == "tool_result":
            inner = block.get("content", "")
            if isinstance(inner, str) and len(inner) > 500:
                return {
                    **block,
                    "content": inner[:200] + f"... [+{len(inner) - 200} chars]",
                    "_trimmed": True,
                }

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
            if msg.get("role") not in ("user", "assistant"):
                key = self._tool_result_key(msg)
                if key:
                    seen[key] = i

        # 第二遍：跳过非最后出现的重复 tool 结果
        for i, msg in enumerate(messages):
            if msg.get("role") not in ("user", "assistant"):
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
        tool_name = msg.get("name") or msg.get("tool_name") or msg.get("role", "tool")
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
            if msg.get("role") != "system":
                reversed_result.append(msg)
                continue

            content = self._msg_to_text(msg)
            bp_key = self._boilerplate_key(content)

            if bp_key:
                if bp_key in seen_boilerplate:
                    # 已有更新的版本，折叠这条
                    saved += self._estimate_tokens(content)
                    reversed_result.append(
                        {
                            **msg,
                            "content": "[boilerplate folded]",
                            "_pass3_folded": True,
                        }
                    )
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
        content = msg.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    parts.append(block.get("text") or block.get("content") or "")
            return " ".join(parts)
        return str(content)

    def _is_base64_blob(self, s: str) -> bool:
        if len(s) < 100:
            return False
        b64_chars = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
        )
        sample = s[:200].replace("\n", "")
        return (
            len(sample) > 0 and sum(c in b64_chars for c in sample) / len(sample) > 0.95
        )

    def _looks_like_json(self, s: str) -> bool:
        stripped = s.strip()
        return (stripped.startswith("{") and stripped.endswith("}")) or (
            stripped.startswith("[") and stripped.endswith("]")
        )

    # ── Pass 4: 消息去重（v4.0.95）──────────────────────────────────────────────

    def _pass4_dedup_messages(
        self, messages: List[Dict]
    ) -> Tuple[List[Dict], int, int]:
        """
        Pass 4: 语义去重消息

        策略：
        - 相同 role + 相似内容 → 只保留第一次出现
        - 相似度阈值：0.8（Jaccard 相似度）
        - 标注重复次数

        Returns:
            (deduped_messages, saved_tokens, dedup_count)
        """
        if not messages:
            return [], 0, 0

        deduped = []
        saved = 0
        dedup_count = 0

        # 按角色分组
        by_role = {}
        for msg in messages:
            role = msg.get("role", "unknown")
            if role not in by_role:
                by_role[role] = []
            by_role[role].append(msg)

        # 对每个角色组进行去重
        # 注意：user 和 assistant 消息不受损无损原则，不进行去重
        for role, group in by_role.items():
            if role in ("user", "assistant"):
                deduped.extend(group)
                continue
            unique = []
            for msg in group:
                content = self._msg_to_text(msg)

                # 检查是否与已有的相似
                is_duplicate = False
                for existing in unique:
                    existing_content = self._msg_to_text(existing)
                    similarity = self._calculate_similarity(content, existing_content)

                    if similarity > 0.8:  # 相似度阈值
                        # 标注重复次数
                        if "_repeat_count" not in existing:
                            existing["_repeat_count"] = 1
                        existing["_repeat_count"] += 1

                        # 计算节省的 tokens
                        saved += self._estimate_tokens(content)
                        dedup_count += 1

                        is_duplicate = True
                        break

                if not is_duplicate:
                    msg["_repeat_count"] = 1
                    unique.append(msg)

            deduped.extend(unique)

        # 按原始顺序排序（保留 seq 字段）
        deduped.sort(key=lambda x: x.get("seq", 0))

        return deduped, saved, dedup_count

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（Jaccard 相似度）

        v4.0.95: 先提取纯文本（去除 JSON 结构），再计算相似度

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            相似度 0-1
        """
        # 提取纯文本
        plain1 = self._extract_plain_text(text1)
        plain2 = self._extract_plain_text(text2)

        # 简单的词频 Jaccard 相似度
        words1 = set(plain1.lower().split())
        words2 = set(plain2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    def _extract_plain_text(self, s: str) -> str:
        """
        从 JSON 字符串中提取纯文本（去除 JSON 结构和转义字符）

        v4.0.95: 递归处理嵌套的 JSON 字符串，提取 text/preview/thinking 等字段

        Args:
            s: 可能包含 JSON 的字符串

        Returns:
            提取的纯文本
        """

        def extract_text(obj):
            if isinstance(obj, dict):
                # 优先提取 text 字段
                if "text" in obj:
                    text = obj["text"]
                    # 如果 text 还是 JSON 字符串，递归提取
                    if isinstance(text, str) and (
                        text.startswith("{") or text.startswith("[")
                    ):
                        try:
                            nested = json.loads(text)
                            extracted = extract_text(nested)
                            if extracted:
                                return extracted
                        except:
                            pass
                    return text
                # 如果没有 text，尝试提取 preview 字段
                elif "preview" in obj:
                    return obj["preview"]
                # 如果没有 preview，尝试提取 thinking 字段
                elif "thinking" in obj:
                    return obj["thinking"]
                # 如果都没有，递归处理所有值
                else:
                    return " ".join(extract_text(v) for v in obj.values() if v)
            elif isinstance(obj, list):
                return " ".join(extract_text(item) for item in obj if item)
            return ""

        try:
            data = json.loads(s)
            return extract_text(data)
        except:
            # 如果不是 JSON，直接返回原文
            return s

    def _estimate_tokens(self, text: str) -> int:
        chinese = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        return int((len(text) - chinese) / 4 + chinese / 1.5)
