"""
技能进化器

借鉴 MemOS Skill Evolution:
  规则过滤 → LLM 评估（可重复/有价值）→ SKILL.md 生成/升级 → 质量评分 → 安装

Version: v5.0.0
"""

import json
import hashlib
from typing import List, Dict, Optional
from datetime import datetime


class SkillEvolver:
    """技能进化器

    流程:
    1. 规则过滤：chitchat/question 类消息跳过
    2. LLM 评估：判断是否可重复、有价值
    3. 生成 SKILL.md
    4. 质量评分（0-1）
    5. 保存到数据库
    """

    SKILL_MIN_CHUNKS = 6  # 与 MemOS skillMinChunks 一致

    def __init__(self, db, llm_client=None):
        """初始化技能进化器

        Args:
            db: LobsterDatabase 实例
            llm_client: BaseLLMClient 实例（用于评估和生成，可选）
        """
        self.db = db
        self.llm_client = llm_client

    def evaluate_and_generate(
        self, task: Dict, conversation_id: str, owner: str = "default"
    ) -> Optional[str]:
        """评估任务并生成技能

        完整流程:
        1. 规则过滤
        2. LLM 评估
        3. 生成 SKILL.md
        4. 质量评分
        5. 保存到数据库

        Args:
            task: 任务字典，包含 goal, steps, result
            conversation_id: 对话 ID
            owner: 技能所有者

        Returns:
            skill_id 或 None（未通过评估）
        """
        # 规则过滤
        if not self._passes_rules(task):
            return None

        # LLM 评估
        if not self._llm_evaluate(task):
            return None

        # 生成 SKILL.md
        skill_md = self._generate_skill_md(task)
        if not skill_md:
            return None

        # 质量评分
        quality = self._score_quality(task, skill_md)

        # 保存
        skill_id = self._save_skill(task, skill_md, quality, conversation_id, owner)

        return skill_id

    def _passes_rules(self, task: Dict) -> bool:
        """规则过滤：跳过不适合生成技能的任务

        过滤条件:
        - 闲聊类关键词
        - 简单问答
        - 测试/Thank you 类

        Args:
            task: 任务字典

        Returns:
            True 表示通过，False 表示过滤
        """
        goal = task.get("goal", "").lower()
        skip_keywords = [
            "你好",
            "hello",
            "hi",
            "嗨",
            "谢谢",
            "thank",
            "thanks",
            "闲聊",
            "chitchat",
            "small talk",
            "测试",
            "test",
            "再见",
            "bye",
            "天气",
            "今天多少度",
        ]
        return not any(kw in goal for kw in skip_keywords)

    def _llm_evaluate(self, task: Dict) -> bool:
        """LLM 评估：判断任务是否可重复、有价值

        不确定时倾向于 NO（避免低质量技能）。

        Args:
            task: 任务字典

        Returns:
            True 表示值得生成技能，False 表示不生成
        """
        if not self.llm_client:
            return True  # 无 LLM 时默认通过

        prompt = f"""评估以下任务是否值得提炼为可复用技能。

任务目标: {task.get("goal", "")}
步骤: {json.dumps(task.get("steps", []), ensure_ascii=False)}
结果: {task.get("result", "")}

判断标准：
1. 该任务是否可重复执行（非一次性操作）
2. 是否包含有价值的技术知识或工作流程

回答 YES 或 NO。不确定时倾向于 NO（避免低质量技能）。
只回答一个词。"""

        try:
            result = self.llm_client.generate(prompt, temperature=0.0, max_tokens=10)
            return "YES" in result.upper()
        except Exception:
            return False

    def _generate_skill_md(self, task: Dict) -> Optional[str]:
        """生成 SKILL.md 内容

        格式借鉴 MemOS:
          步骤/警告/脚本

        Args:
            task: 任务字典

        Returns:
            SKILL.md 格式字符串
        """
        if self.llm_client:
            try:
                prompt = f"""基于以下任务信息，生成一个 SKILL.md 技能文件。

任务目标: {task.get("goal", "")}
步骤: {json.dumps(task.get("steps", []), ensure_ascii=False)}
结果: {task.get("result", "")}

格式要求：
# 技能名称
## 目标
一句话描述
## 步骤
1. ...
2. ...
## 警告
- ...
## 脚本（可选）
```bash
...
```

只返回 Markdown 内容。"""

                return self.llm_client.generate(prompt, temperature=0.3, max_tokens=800)
            except Exception:
                pass

        # 降级：模板生成
        steps_md = "\n".join(
            f"{i + 1}. {s}" for i, s in enumerate(task.get("steps", []))
        )
        return f"""# {task.get("goal", "未命名技能")[:50]}

## 目标
{task.get("goal", "")}

## 步骤
{steps_md}

## 警告
- 此技能由规则模板自动生成，建议人工审核
"""

    def _score_quality(self, task: Dict, skill_md: str) -> float:
        """质量评分（0-1）

        评分维度：
        1. 步骤完整性（有步骤 = +0.3）
        2. 结果明确性（有结果 = +0.2）
        3. 内容长度（>200字 = +0.2）
        4. 有脚本（+0.15）
        5. 有警告（+0.15）

        Args:
            task: 任务字典
            skill_md: 生成的 SKILL.md 内容

        Returns:
            质量分数 0.0-1.0
        """
        score = 0.0

        # 步骤完整性
        if task.get("steps") and len(task["steps"]) >= 2:
            score += 0.3

        # 结果明确性
        if task.get("result") and len(task["result"]) > 20:
            score += 0.2

        # 内容长度
        if len(skill_md) > 200:
            score += 0.2

        # 有脚本
        if "```" in skill_md:
            score += 0.15

        # 有警告
        if "## 警告" in skill_md or "## Warnings" in skill_md:
            score += 0.15

        return min(score, 1.0)

    def _save_skill(
        self,
        task: Dict,
        skill_md: str,
        quality: float,
        conversation_id: str,
        owner: str,
    ) -> str:
        """保存技能到数据库

        Args:
            task: 任务字典
            skill_md: SKILL.md 内容
            quality: 质量分数
            conversation_id: 对话 ID
            owner: 所有者

        Returns:
            skill_id
        """
        from .models import Skill

        goal = task.get("goal", "untitled")[:50]
        skill_id = f"skill_{hashlib.sha256((owner + goal).encode()).hexdigest()[:16]}"
        now = datetime.utcnow().isoformat()

        skill = Skill(
            skill_id=skill_id,
            name=goal,
            description=task.get("result", ""),
            owner=owner,
            visibility="private",
            quality_score=quality,
            version=1,
            steps=task.get("steps", []),
            warnings=[],
            script="",
            source_task_ids=[conversation_id],
            created_at=now,
            updated_at=now,
        )

        # 保存主记录
        self.db.save_skill(skill)

        # 保存版本
        self.db.save_skill_version(skill_id, 1, skill_md, quality)

        # 关联任务
        self.db.save_task_skill(conversation_id, skill_id)

        return skill_id
