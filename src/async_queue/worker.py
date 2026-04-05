"""
异步任务队列

借鉴 MemOS:
  异步队列：语义分片 → LLM 摘要 → Embed → 智能去重 → 存储
  任务检测、技能进化也走此队列

Version: v5.0.0
"""

import asyncio
import threading
import time
from typing import Callable, Dict, Any, Optional
from collections import deque
from datetime import datetime


class AsyncWorker:
    """异步任务队列处理器

    使用后台守护线程处理异步任务：
    - embed: 向量化任务
    - task_detect: 任务检测
    - skill_eval: 技能评估

    Args:
        db: LobsterDatabase 实例
        embedder: BaseEmbedder 实例（可选）
        llm_client: BaseLLMClient 实例（可选）
    """

    def __init__(self, db, embedder=None, llm_client=None):
        self.db = db
        self.embedder = embedder
        self.llm_client = llm_client
        self._queue: deque = deque()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self):
        """启动后台工作线程"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止后台工作线程"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def enqueue(self, task_type: str, payload: Dict[str, Any]):
        """入队任务

        Args:
            task_type: 任务类型 ('embed', 'task_detect', 'skill_eval')
            payload: 任务参数
        """
        with self._lock:
            self._queue.append(
                {
                    "type": task_type,
                    "payload": payload,
                    "enqueued_at": datetime.utcnow().isoformat(),
                }
            )

    def _run_loop(self):
        """后台任务处理循环"""
        while self._running:
            task = self._dequeue()
            if task is None:
                time.sleep(0.1)
                continue

            try:
                self._process(task)
            except Exception as e:
                print(f"⚠️ Async task [{task['type']}] failed: {e}")

    def _dequeue(self) -> Optional[Dict]:
        """从队列取出任务"""
        with self._lock:
            if self._queue:
                return self._queue.popleft()
            return None

    def _process(self, task: Dict):
        """处理单个任务

        Args:
            task: 包含 type 和 payload 的字典
        """
        task_type = task["type"]
        payload = task["payload"]

        if task_type == "embed":
            self._process_embed(payload)
        elif task_type == "task_detect":
            self._process_task_detect(payload)
        elif task_type == "skill_eval":
            self._process_skill_eval(payload)
        else:
            print(f"⚠️ Unknown task type: {task_type}")

    def _process_embed(self, payload: Dict):
        """异步嵌入：向量化消息/摘要

        Args:
            payload: 包含 target_type, target_id, content
        """
        target_type = payload.get("target_type")
        target_id = payload.get("target_id")
        content = payload.get("content", "")

        if not target_type or not target_id:
            print("⚠️ embed: missing target_type or target_id")
            return

        if not self.embedder or not self.embedder.is_available():
            print("⚠️ embed: embedder not available")
            return

        try:
            vec = self.embedder.embed(content)
            self.db.save_embedding(target_type, target_id, vec)
        except Exception as e:
            print(f"⚠️ embed failed: {e}")

    def _process_task_detect(self, payload: Dict):
        """异步任务检测

        Args:
            payload: 包含 conversation_id
        """
        conversation_id = payload.get("conversation_id")

        if not conversation_id:
            print("⚠️ task_detect: missing conversation_id")
            return

        if not self.llm_client:
            print("⚠️ task_detect: llm_client not available")
            return

        try:
            from ..skills.task_detector import TaskDetector

            detector = TaskDetector(self.db, self.llm_client)
            tasks = detector.detect_tasks(conversation_id)
            return tasks
        except Exception as e:
            print(f"⚠️ task_detect failed: {e}")
            return None

    def _process_skill_eval(self, payload: Dict):
        """异步技能评估

        Args:
            payload: 包含 conversation_id, task
        """
        conversation_id = payload.get("conversation_id")
        task = payload.get("task")

        if not conversation_id or not task:
            print("⚠️ skill_eval: missing conversation_id or task")
            return

        if not self.llm_client:
            print("⚠️ skill_eval: llm_client not available")
            return

        try:
            from ..skills.evolver import SkillEvolver

            evolver = SkillEvolver(self.db, self.llm_client)
            skill_id = evolver.evaluate_and_generate(task, conversation_id)
            return skill_id
        except Exception as e:
            print(f"⚠️ skill_eval failed: {e}")
            return None

    @property
    def queue_size(self) -> int:
        """返回当前队列大小"""
        with self._lock:
            return len(self._queue)

    def is_running(self) -> bool:
        """返回是否正在运行"""
        return self._running and self._thread is not None and self._thread.is_alive()
