"""异步任务队列模块 for lobster-press v5.0.

借鉴 MemOS Ingest 异步队列:
  语义分片 → LLM 摘要 → Embed → 智能去重 → 存储
  任务检测、技能进化也走此队列
"""

from .worker import AsyncWorker

__all__ = ["AsyncWorker"]
