"""
技能进化数据模型

借鉴 MemOS:
  skills 表: owner, visibility, quality_score
  skill_versions 表: 版本追踪
  task_skills 表: 任务→技能关联

Version: v5.0.0
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Skill:
    """技能数据模型

    Attributes:
        skill_id: 技能唯一标识 (SHA-256 hash)
        name: 技能名称
        description: 技能描述
        owner: 所有者 ('agent:{agentId}' 或 'public')
        visibility: 可见性 ('private' | 'public')
        quality_score: 质量评分 (0.0-1.0)
        version: 当前版本号
        steps: 执行步骤列表
        warnings: 警告列表
        script: 可选脚本
        source_task_ids: 来源任务 ID 列表
        created_at: 创建时间
        updated_at: 更新时间
    """

    skill_id: str
    name: str
    description: str = ""
    owner: str = "default"
    visibility: str = "private"
    quality_score: float = 0.0
    version: int = 1
    steps: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    script: str = ""
    source_task_ids: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "owner": self.owner,
            "visibility": self.visibility,
            "quality_score": self.quality_score,
            "version": self.version,
            "steps": self.steps,
            "warnings": self.warnings,
            "script": self.script,
            "source_task_ids": self.source_task_ids,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class TaskSummary:
    """任务摘要数据模型

    表示一个检测到的任务边界及其结构化摘要。

    Attributes:
        task_id: 任务唯一标识
        conversation_id: 所属对话 ID
        owner: 所有者
        goal: 任务目标
        steps: 执行步骤
        result: 执行结果
        status: 状态 ('active' | 'completed')
        created_at: 创建时间
        skill_generated: 是否已生成技能
    """

    task_id: str
    conversation_id: str
    owner: str = "default"
    goal: str = ""
    steps: List[str] = field(default_factory=list)
    result: str = ""
    status: str = "completed"
    created_at: str = ""
    skill_generated: bool = False

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "conversation_id": self.conversation_id,
            "owner": self.owner,
            "goal": self.goal,
            "steps": self.steps,
            "result": self.result,
            "status": self.status,
            "created_at": self.created_at,
            "skill_generated": self.skill_generated,
        }
