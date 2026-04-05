"""Skill evolution module for lobster-press v5.0.

借鉴 MemOS Skill Evolution pipeline:
  规则过滤 → LLM 评估（可重复/有价值）→ SKILL.md 生成/升级 → 质量评分 → 安装
"""

from .models import Skill, TaskSummary

__all__ = ["Skill", "TaskSummary"]
