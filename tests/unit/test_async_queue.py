"""
Unit tests for AsyncWorker module.
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from collections import deque


class TestAsyncWorkerStartStop:
    """Tests for start/stop functionality."""

    def test_start_sets_running_and_creates_thread(self):
        """start() should set _running=True and create daemon thread."""
        from src.async_queue import AsyncWorker

        worker = AsyncWorker(db=MagicMock())
        assert worker._running is False
        assert worker._thread is None

        worker.start()

        assert worker._running is True
        assert worker._thread is not None
        assert worker._thread.daemon is True
        assert worker._thread.is_alive() is True

        worker.stop()
        time.sleep(0.2)
        assert worker._running is False

    def test_stop_sets_running_false_and_joins_thread(self):
        """stop() should set _running=False and join thread."""
        from src.async_queue import AsyncWorker

        worker = AsyncWorker(db=MagicMock())
        worker.start()
        assert worker.is_running() is True

        worker.stop()
        time.sleep(0.3)

        assert worker._running is False
        assert worker._thread is None

    def test_is_running_reflects_actual_state(self):
        """is_running() should reflect actual running state."""
        from src.async_queue import AsyncWorker

        worker = AsyncWorker(db=MagicMock())
        assert worker.is_running() is False

        worker.start()
        assert worker.is_running() is True

        worker.stop()
        time.sleep(0.3)
        assert worker.is_running() is False


class TestEnqueueDequeue:
    """Tests for enqueue/dequeue functionality."""

    def test_enqueue_adds_to_queue(self):
        """enqueue should add task to internal queue."""
        from src.async_queue import AsyncWorker

        worker = AsyncWorker(db=MagicMock())
        worker.enqueue(
            "embed", {"target_type": "message", "target_id": "123", "content": "hello"}
        )

        assert worker.queue_size == 1

    def test_queue_size_reflects_correct_count(self):
        """queue_size should reflect correct count."""
        from src.async_queue import AsyncWorker

        worker = AsyncWorker(db=MagicMock())
        assert worker.queue_size == 0

        worker.enqueue("embed", {"target_type": "msg", "target_id": "1", "content": ""})
        assert worker.queue_size == 1

        worker.enqueue("task_detect", {"conversation_id": "conv1"})
        assert worker.queue_size == 2

        worker.enqueue("skill_eval", {"conversation_id": "conv1", "task": {}})
        assert worker.queue_size == 3

    def test_empty_queue_returns_none_from_dequeue(self):
        """Empty queue should return None from _dequeue."""
        from src.async_queue import AsyncWorker

        worker = AsyncWorker(db=MagicMock())
        result = worker._dequeue()

        assert result is None


class TestProcessDispatch:
    """Tests for _process dispatch."""

    def test_calls_correct_handler_for_each_task_type(self):
        """_process should call correct handler for each task type."""
        from src.async_queue import AsyncWorker

        worker = AsyncWorker(db=MagicMock())

        with (
            patch.object(worker, "_process_embed") as mock_embed,
            patch.object(worker, "_process_task_detect") as mock_detect,
            patch.object(worker, "_process_skill_eval") as mock_skill,
        ):
            worker._process({"type": "embed", "payload": {}})
            mock_embed.assert_called_once_with({})
            mock_embed.reset_mock()

            worker._process({"type": "task_detect", "payload": {}})
            mock_detect.assert_called_once_with({})
            mock_detect.reset_mock()

            worker._process({"type": "skill_eval", "payload": {}})
            mock_skill.assert_called_once_with({})

    def test_unknown_task_type_logged_as_warning(self):
        """Unknown task type should be logged as warning."""
        from src.async_queue import AsyncWorker

        worker = AsyncWorker(db=MagicMock())

        with patch("builtins.print") as mock_print:
            worker._process({"type": "unknown_type", "payload": {}})
            mock_print.assert_called_once()
            assert "Unknown task type" in mock_print.call_args[0][0]


class TestProcessEmbed:
    """Tests for _process_embed handler."""

    def test_skips_when_embedder_not_available(self):
        """Should skip when embedder is None or not available."""
        from src.async_queue import AsyncWorker

        worker = AsyncWorker(db=MagicMock(), embedder=None)

        with patch("builtins.print") as mock_print:
            worker._process_embed(
                {"target_type": "msg", "target_id": "123", "content": "test"}
            )
            mock_print.assert_called_once_with("⚠️ embed: embedder not available")

    def test_skips_when_missing_target_type_or_id(self):
        """Should skip when target_type or target_id is missing."""
        from src.async_queue import AsyncWorker

        mock_embedder = MagicMock()
        mock_embedder.is_available.return_value = True
        worker = AsyncWorker(db=MagicMock(), embedder=mock_embedder)

        with patch("builtins.print") as mock_print:
            worker._process_embed(
                {"target_type": "", "target_id": "123", "content": "test"}
            )
            assert any(
                "missing target_type or target_id" in str(arg)
                for arg in mock_print.call_args_list
            )

    def test_calls_embedder_and_save_embedding(self):
        """Should call embedder.embed() and db.save_embedding()."""
        from src.async_queue import AsyncWorker

        mock_embedder = MagicMock()
        mock_embedder.is_available.return_value = True
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]
        mock_db = MagicMock()

        worker = AsyncWorker(db=mock_db, embedder=mock_embedder)

        worker._process_embed(
            {"target_type": "message", "target_id": "msg_123", "content": "hello world"}
        )

        mock_embedder.embed.assert_called_once_with("hello world")
        mock_db.save_embedding.assert_called_once_with(
            "message", "msg_123", [0.1, 0.2, 0.3]
        )


class TestProcessTaskDetect:
    """Tests for _process_task_detect handler."""

    def test_skips_when_no_llm_client(self):
        """Should skip when llm_client is None."""
        from src.async_queue import AsyncWorker

        worker = AsyncWorker(db=MagicMock(), llm_client=None)

        with patch("builtins.print") as mock_print:
            worker._process_task_detect({"conversation_id": "conv1"})
            mock_print.assert_called_once_with(
                "⚠️ task_detect: llm_client not available"
            )

    def test_skips_when_missing_conversation_id(self):
        """Should skip when conversation_id is missing."""
        from src.async_queue import AsyncWorker

        worker = AsyncWorker(db=MagicMock(), llm_client=MagicMock())

        with patch("builtins.print") as mock_print:
            worker._process_task_detect({})
            mock_print.assert_called_once()
            assert "missing conversation_id" in mock_print.call_args[0][0]

    @patch("src.skills.task_detector.TaskDetector")
    def test_uses_task_detector_and_returns_tasks(self, mock_detector_class):
        """Should use TaskDetector and return tasks."""
        from src.async_queue import AsyncWorker

        mock_detector = MagicMock()
        mock_detector.detect_tasks.return_value = ["task1", "task2"]
        mock_detector_class.return_value = mock_detector

        mock_llm = MagicMock()
        mock_db = MagicMock()

        worker = AsyncWorker(db=mock_db, llm_client=mock_llm)
        result = worker._process_task_detect({"conversation_id": "conv123"})

        mock_detector_class.assert_called_once_with(mock_db, mock_llm)
        mock_detector.detect_tasks.assert_called_once_with("conv123")
        assert result == ["task1", "task2"]


class TestProcessSkillEval:
    """Tests for _process_skill_eval handler."""

    def test_skips_when_no_llm_client(self):
        """Should skip when llm_client is None."""
        from src.async_queue import AsyncWorker

        worker = AsyncWorker(db=MagicMock(), llm_client=None)

        with patch("builtins.print") as mock_print:
            worker._process_skill_eval(
                {"conversation_id": "conv1", "task": {"type": "test"}}
            )
            mock_print.assert_called_once_with("⚠️ skill_eval: llm_client not available")

    def test_skips_when_missing_conversation_id_or_task(self):
        """Should skip when conversation_id or task is missing."""
        from src.async_queue import AsyncWorker

        worker = AsyncWorker(db=MagicMock(), llm_client=MagicMock())

        with patch("builtins.print") as mock_print:
            worker._process_skill_eval({"conversation_id": "conv1"})
            assert any(
                "missing conversation_id or task" in str(arg)
                for arg in mock_print.call_args_list
            )

        with patch("builtins.print") as mock_print:
            worker._process_skill_eval({"task": {}})
            assert any(
                "missing conversation_id or task" in str(arg)
                for arg in mock_print.call_args_list
            )

    @patch("src.skills.evolver.SkillEvolver")
    def test_uses_skill_evolver_and_returns_skill_id(self, mock_evolver_class):
        """Should use SkillEvolver and return skill_id."""
        from src.async_queue import AsyncWorker

        mock_evolver = MagicMock()
        mock_evolver.evaluate_and_generate.return_value = "skill_456"
        mock_evolver_class.return_value = mock_evolver

        mock_llm = MagicMock()
        mock_db = MagicMock()
        task = {"type": "coding", "description": "write tests"}

        worker = AsyncWorker(db=mock_db, llm_client=mock_llm)
        result = worker._process_skill_eval(
            {"conversation_id": "conv123", "task": task}
        )

        mock_evolver_class.assert_called_once_with(mock_db, mock_llm)
        mock_evolver.evaluate_and_generate.assert_called_once_with(task, "conv123")
        assert result == "skill_456"


class TestErrorHandling:
    """Tests for error handling."""

    def test_exceptions_in_process_are_caught_and_logged(self):
        """Exceptions in _process should be caught and logged via _run_loop."""
        import threading
        from src.async_queue import AsyncWorker

        worker = AsyncWorker(db=MagicMock())
        mock_embedder = MagicMock()
        mock_embedder.is_available.return_value = True
        mock_embedder.embed.side_effect = ValueError("embed error")
        worker.embedder = mock_embedder

        worker.enqueue(
            "embed", {"target_type": "msg", "target_id": "123", "content": "test"}
        )
        worker._running = True

        with patch("builtins.print") as mock_print:
            t = threading.Thread(target=worker._run_loop)
            t.start()
            t.join(timeout=2.0)
            worker._running = False

            assert mock_print.call_count > 0, (
                f"print was never called. calls={mock_print.call_args_list}"
            )
            print_args = [str(c) for c in mock_print.call_args_list]
            assert any("embed failed" in p for p in print_args), (
                f"Expected error message not found in {print_args}"
            )

    def test_worker_continues_after_error(self):
        """Worker should continue processing after an error."""
        from src.async_queue import AsyncWorker

        worker = AsyncWorker(db=MagicMock())
        worker.start()

        call_count = [0]
        original_process = worker._process

        def track_process(task):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("first error")

        with patch.object(worker, "_process", side_effect=track_process):
            worker.enqueue("embed", {"content": "first"})
            time.sleep(0.05)
            worker.enqueue("task_detect", {"conversation_id": "conv1"})
            time.sleep(0.3)

        worker.stop()
