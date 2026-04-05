"""
任务边界检测器

借鉴 MemOS Task Summarization:
  异步逐轮检测任务边界：用户回合分组 → LLM 话题判断 → 2h 超时切分 → 结构化摘要

Version: v5.0.0
"""

import json
from typing import List, Dict, Optional
from datetime import datetime


class TaskDetector:
    """任务边界检测器

    检测算法：
    1. 按用户回合分组（连续 user 消息 → 一个回合）
    2. 第一回合直接分配为新任务
    3. 后续回合：
       a. 时间间隔 > 2h → 强制切分
       b. LLM 判断话题是否切换（偏向 SAME）
    4. 为每个任务生成结构化摘要（goal/steps/result）
    """

    TOPIC_IDLE_HOURS = 2.0  # 与 MemOS taskIdle 一致
    SKILL_MIN_CHUNKS = 6  # 与 MemOS skillMinChunks 一致

    def __init__(self, db, llm_client=None):
        """初始化任务检测器

        Args:
            db: LobsterDatabase 实例
            llm_client: BaseLLMClient 实例（用于话题判断，可选）
        """
        self.db = db
        self.llm_client = llm_client

    def detect_tasks(self, conversation_id: str) -> List[Dict]:
        """从对话消息中检测任务边界

        Args:
            conversation_id: 对话 ID

        Returns:
            任务列表，每项包含 goal, steps, result
        """
        messages = self.db.get_messages(conversation_id)
        if not messages:
            return []

        # 分组为用户回合
        turns = self._group_user_turns(messages)

        # 检测任务边界
        tasks = []
        current_task_turns = []

        for i, turn in enumerate(turns):
            if i == 0:
                current_task_turns.append(turn)
                continue

            # 2h 超时强制切分
            prev_time = self._get_turn_time(current_task_turns[-1])
            curr_time = self._get_turn_time(turn)
            if prev_time and curr_time:
                gap_hours = (curr_time - prev_time).total_seconds() / 3600.0
                if gap_hours > self.TOPIC_IDLE_HOURS:
                    if current_task_turns:
                        tasks.append(
                            self._summarize_task(current_task_turns, conversation_id)
                        )
                    current_task_turns = [turn]
                    continue

            # LLM 话题判断（偏向 SAME）
            if self.llm_client and len(current_task_turns) >= 1:
                is_same_topic = self._llm_judge_topic(current_task_turns, turn)
                if not is_same_topic:
                    tasks.append(
                        self._summarize_task(current_task_turns, conversation_id)
                    )
                    current_task_turns = [turn]
                    continue

            current_task_turns.append(turn)

        # 最后一个任务
        if current_task_turns:
            tasks.append(self._summarize_task(current_task_turns, conversation_id))

        return tasks

    def _group_user_turns(self, messages: List[Dict]) -> List[List[Dict]]:
        """将消息按用户回合分组

        连续的用户消息被归为同一回合。

        Args:
            messages: 消息列表

        Returns:
            用户回合列表，每个回合包含多条消息
        """
        turns = []
        current_turn = []

        for msg in messages:
            role = msg.get("role", "")
            if role == "user" and current_turn:
                # 新的用户消息开始新回合
                turns.append(current_turn)
                current_turn = [msg]
            else:
                current_turn.append(msg)

        if current_turn:
            turns.append(current_turn)

        return turns

    def _llm_judge_topic(
        self, prev_turns: List[List[Dict]], new_turn: List[Dict]
    ) -> bool:
        """LLM 话题判断（强偏向 SAME）

        返回 True 表示同一话题，False 表示话题切换。
        失败时默认 SAME 以避免过度分割。

        Args:
            prev_turns: 之前的回合列表
            new_turn: 新的单个回合

        Returns:
            True 表示同一话题，False 表示切换
        """
        prev_text = " ".join(
            m.get("content", "")[:200] for turn in prev_turns[-2:] for m in turn
        )[:1000]
        new_text = " ".join(m.get("content", "")[:200] for m in new_turn)[:500]

        prompt = f"""判断以下两段对话是否属于同一任务话题。

之前的对话: {prev_text}
新的对话: {new_text}

请回答 SAME 或 NEW。如果不确定，倾向于 SAME（避免过度分割）。
只回答一个词。"""

        try:
            result = self.llm_client.generate(prompt, temperature=0.0, max_tokens=10)
            return "NEW" not in result.upper()
        except Exception:
            return True  # 失败时偏向 SAME

    def _summarize_task(self, turns: List[List[Dict]], conversation_id: str) -> Dict:
        """生成任务结构化摘要

        尝试 LLM 生成 {goal, steps, result} JSON，
        失败时降级为提取式摘要。

        Args:
            turns: 回合列表
            conversation_id: 对话 ID

        Returns:
            包含 goal, steps, result 的字典
        """
        all_msgs = [m for turn in turns for m in turn]
        combined = "\n".join(
            f"[{m.get('role', '?')}]: {m.get('content', '')[:300]}"
            for m in all_msgs[:30]
        )

        if self.llm_client:
            try:
                prompt = f"""从以下对话片段中提取结构化任务摘要。

返回 JSON 格式:
{{"goal": "...", "steps": ["...", "..."], "result": "..."}}

对话内容:
{combined}

只返回 JSON，不要其他文字。"""
                raw = self.llm_client.generate(prompt, temperature=0.3, max_tokens=500)
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    result = json.loads(raw[start:end])
                    # 确保字段完整
                    return {
                        "goal": result.get("goal", ""),
                        "steps": result.get("steps", []),
                        "result": result.get("result", ""),
                    }
            except Exception:
                pass

        # 降级：提取式摘要
        return {
            "goal": all_msgs[0].get("content", "")[:100] if all_msgs else "",
            "steps": [m.get("content", "")[:80] for m in all_msgs[:5]],
            "result": all_msgs[-1].get("content", "")[:100] if all_msgs else "",
        }

    def _get_turn_time(self, turn: List[Dict]) -> Optional[datetime]:
        """获取回合的时间戳

        使用回合中第一条消息的时间戳。

        Args:
            turn: 回合消息列表

        Returns:
            datetime 对象或 None
        """
        for msg in turn:
            ts = msg.get("created_at") or msg.get("timestamp")
            if ts:
                try:
                    return datetime.fromisoformat(ts)
                except (ValueError, TypeError):
                    continue
        return None
