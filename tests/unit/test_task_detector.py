"""
Unit tests for TaskDetector module.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, response: str = "SAME"):
        self.response = response
        self.call_count = 0
        self.last_prompt = None

    def generate(
        self, prompt: str, temperature: float = 0.0, max_tokens: int = 10
    ) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        return self.response


class TestGroupUserTurns:
    """Tests for _group_user_turns method."""

    def test_consecutive_user_messages_create_separate_turns(self):
        """Consecutive user messages each start new turns."""
        from src.skills.task_detector import TaskDetector

        detector = TaskDetector(db=MagicMock())
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "user", "content": "World"},
        ]
        turns = detector._group_user_turns(messages)

        assert len(turns) == 2
        assert turns[0][0]["content"] == "Hello"
        assert turns[1][0]["content"] == "World"

    def test_assistant_messages_follow_user_in_same_turn(self):
        """Assistant messages should follow user message in same turn."""
        from src.skills.task_detector import TaskDetector

        detector = TaskDetector(db=MagicMock())
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        turns = detector._group_user_turns(messages)

        assert len(turns) == 1
        assert len(turns[0]) == 2

    def test_empty_input_returns_empty_list(self):
        """Empty input should return empty list."""
        from src.skills.task_detector import TaskDetector

        detector = TaskDetector(db=MagicMock())
        turns = detector._group_user_turns([])

        assert turns == []

    def test_single_message_returns_single_turn(self):
        """Single message should return single turn."""
        from src.skills.task_detector import TaskDetector

        detector = TaskDetector(db=MagicMock())
        messages = [{"role": "user", "content": "Hello"}]
        turns = detector._group_user_turns(messages)

        assert len(turns) == 1
        assert len(turns[0]) == 1


class TestLLMJudgeTopic:
    """Tests for _llm_judge_topic method."""

    def test_llm_returns_same_returns_true(self):
        """When LLM returns SAME, should return True."""
        from src.skills.task_detector import TaskDetector

        mock_llm = MockLLMClient(response="SAME")
        detector = TaskDetector(db=MagicMock(), llm_client=mock_llm)

        prev_turns = [[{"role": "user", "content": "old content"}]]
        new_turn = [{"role": "user", "content": "new content"}]

        result = detector._llm_judge_topic(prev_turns, new_turn)

        assert result is True

    def test_llm_returns_new_returns_false(self):
        """When LLM returns NEW, should return False."""
        from src.skills.task_detector import TaskDetector

        mock_llm = MockLLMClient(response="NEW")
        detector = TaskDetector(db=MagicMock(), llm_client=mock_llm)

        prev_turns = [[{"role": "user", "content": "old content"}]]
        new_turn = [{"role": "user", "content": "new content"}]

        result = detector._llm_judge_topic(prev_turns, new_turn)

        assert result is False

    def test_llm_failure_defaults_to_same(self):
        """When LLM fails, should default to True (SAME)."""
        from src.skills.task_detector import TaskDetector

        class FailingLLM:
            def generate(self, prompt, temperature=0.0, max_tokens=10):
                raise Exception("LLM failure")

        detector = TaskDetector(db=MagicMock(), llm_client=FailingLLM())

        prev_turns = [[{"role": "user", "content": "old content"}]]
        new_turn = [{"role": "user", "content": "new content"}]

        result = detector._llm_judge_topic(prev_turns, new_turn)

        assert result is True

    def test_prompt_contains_prev_and_new_text(self):
        """Prompt should contain both previous and new text."""
        from src.skills.task_detector import TaskDetector

        mock_llm = MockLLMClient(response="SAME")
        detector = TaskDetector(db=MagicMock(), llm_client=mock_llm)

        prev_turns = [[{"role": "user", "content": "previous message"}]]
        new_turn = [{"role": "user", "content": "new message"}]

        detector._llm_judge_topic(prev_turns, new_turn)

        assert "previous message" in mock_llm.last_prompt
        assert "new message" in mock_llm.last_prompt


class TestGetTurnTime:
    """Tests for _get_turn_time method."""

    def test_returns_datetime_from_created_at(self):
        """Should return datetime from created_at field."""
        from src.skills.task_detector import TaskDetector

        detector = TaskDetector(db=MagicMock())
        turn = [{"created_at": "2026-03-17T10:00:00", "content": "test"}]

        result = detector._get_turn_time(turn)

        assert result == datetime(2026, 3, 17, 10, 0, 0)

    def test_falls_back_to_timestamp(self):
        """Should fall back to timestamp if created_at missing."""
        from src.skills.task_detector import TaskDetector

        detector = TaskDetector(db=MagicMock())
        turn = [{"timestamp": "2026-03-17T12:30:00", "content": "test"}]

        result = detector._get_turn_time(turn)

        assert result == datetime(2026, 3, 17, 12, 30, 0)

    def test_returns_none_for_empty_turn(self):
        """Should return None for empty turn."""
        from src.skills.task_detector import TaskDetector

        detector = TaskDetector(db=MagicMock())

        result = detector._get_turn_time([])

        assert result is None

    def test_returns_none_when_no_valid_timestamp(self):
        """Should return None when no valid timestamp exists."""
        from src.skills.task_detector import TaskDetector

        detector = TaskDetector(db=MagicMock())
        turn = [{"content": "no timestamp here"}, {"role": "user"}]

        result = detector._get_turn_time(turn)

        assert result is None


class TestSummarizeTask:
    """Tests for _summarize_task method."""

    def test_with_llm_extracts_json_goal_steps_result(self):
        """With LLM, should extract JSON {goal, steps, result}."""
        from src.skills.task_detector import TaskDetector

        mock_llm = MockLLMClient(
            response='{"goal": "test goal", "steps": ["step1", "step2"], "result": "done"}'
        )
        detector = TaskDetector(db=MagicMock(), llm_client=mock_llm)

        turns = [[{"role": "user", "content": "test content"}]]
        result = detector._summarize_task(turns, "conv123")

        assert result["goal"] == "test goal"
        assert result["steps"] == ["step1", "step2"]
        assert result["result"] == "done"

    def test_without_llm_returns_extractive_fallback(self):
        """Without LLM, should return extractive fallback."""
        from src.skills.task_detector import TaskDetector

        detector = TaskDetector(db=MagicMock(), llm_client=None)

        turns = [
            [
                {"role": "user", "content": "first message"},
                {"role": "assistant", "content": "response"},
            ]
        ]
        result = detector._summarize_task(turns, "conv123")

        assert "goal" in result
        assert "steps" in result
        assert "result" in result

    def test_handles_malformed_json_gracefully(self):
        """Should handle malformed JSON gracefully."""
        from src.skills.task_detector import TaskDetector

        mock_llm = MockLLMClient(response="not valid json at all")
        detector = TaskDetector(db=MagicMock(), llm_client=mock_llm)

        turns = [[{"role": "user", "content": "test content"}]]
        result = detector._summarize_task(turns, "conv123")

        # Should still return a valid dict with extractive fallback
        assert "goal" in result
        assert "steps" in result
        assert "result" in result

    def test_handles_llm_failure_gracefully(self):
        """Should handle LLM failure gracefully."""
        from src.skills.task_detector import TaskDetector

        class FailingLLM:
            def generate(self, prompt, temperature=0.0, max_tokens=10):
                raise Exception("LLM failure")

        detector = TaskDetector(db=MagicMock(), llm_client=FailingLLM())

        turns = [[{"role": "user", "content": "test content"}]]
        result = detector._summarize_task(turns, "conv123")

        # Should still return a valid dict with extractive fallback
        assert "goal" in result
        assert "steps" in result
        assert "result" in result


class TestDetectTasks:
    """Tests for detect_tasks method."""

    def test_two_hour_gap_forces_split(self):
        """2h+ time gap should force task split."""
        from src.skills.task_detector import TaskDetector

        mock_llm = MockLLMClient(response="SAME")
        detector = TaskDetector(db=MagicMock(), llm_client=mock_llm)

        base_time = datetime(2026, 3, 17, 10, 0, 0)
        messages = [
            {"role": "user", "content": "task 1", "created_at": base_time.isoformat()},
            {
                "role": "assistant",
                "content": "response 1",
                "created_at": base_time.isoformat(),
            },
            {
                "role": "user",
                "content": "task 2",
                "created_at": (base_time + timedelta(hours=3)).isoformat(),
            },
        ]

        detector.db.get_messages = MagicMock(return_value=messages)

        tasks = detector.detect_tasks("conv123")

        assert len(tasks) == 2

    def test_llm_same_keeps_same_task(self):
        """LLM returning SAME should keep messages in same task."""
        from src.skills.task_detector import TaskDetector

        mock_llm = MockLLMClient(response="SAME")
        detector = TaskDetector(db=MagicMock(), llm_client=mock_llm)

        base_time = datetime(2026, 3, 17, 10, 0, 0)
        messages = [
            {"role": "user", "content": "task 1", "created_at": base_time.isoformat()},
            {
                "role": "assistant",
                "content": "response 1",
                "created_at": base_time.isoformat(),
            },
            {
                "role": "user",
                "content": "same topic",
                "created_at": (base_time + timedelta(minutes=30)).isoformat(),
            },
        ]

        detector.db.get_messages = MagicMock(return_value=messages)

        tasks = detector.detect_tasks("conv123")

        assert len(tasks) == 1

    def test_llm_new_splits_task(self):
        """LLM returning NEW should split task."""
        from src.skills.task_detector import TaskDetector

        mock_llm = MockLLMClient(response="NEW")
        detector = TaskDetector(db=MagicMock(), llm_client=mock_llm)

        base_time = datetime(2026, 3, 17, 10, 0, 0)
        messages = [
            {"role": "user", "content": "task 1", "created_at": base_time.isoformat()},
            {
                "role": "assistant",
                "content": "response 1",
                "created_at": base_time.isoformat(),
            },
            {
                "role": "user",
                "content": "new topic",
                "created_at": (base_time + timedelta(minutes=30)).isoformat(),
            },
        ]

        detector.db.get_messages = MagicMock(return_value=messages)

        tasks = detector.detect_tasks("conv123")

        assert len(tasks) == 2

    def test_first_turn_always_starts_new_task(self):
        """First turn should always start a new task."""
        from src.skills.task_detector import TaskDetector

        mock_llm = MockLLMClient(response="NEW")
        detector = TaskDetector(db=MagicMock(), llm_client=mock_llm)

        base_time = datetime(2026, 3, 17, 10, 0, 0)
        messages = [
            {
                "role": "user",
                "content": "first task",
                "created_at": base_time.isoformat(),
            },
        ]

        detector.db.get_messages = MagicMock(return_value=messages)

        tasks = detector.detect_tasks("conv123")

        assert len(tasks) == 1

    def test_returns_list_of_task_dicts_with_goal_steps_result(self):
        """Should return list of task dicts with goal/steps/result."""
        from src.skills.task_detector import TaskDetector

        mock_llm = MockLLMClient(
            response='{"goal": "test goal", "steps": ["step1"], "result": "done"}'
        )
        detector = TaskDetector(db=MagicMock(), llm_client=mock_llm)

        base_time = datetime(2026, 3, 17, 10, 0, 0)
        messages = [
            {"role": "user", "content": "task", "created_at": base_time.isoformat()},
        ]

        detector.db.get_messages = MagicMock(return_value=messages)

        tasks = detector.detect_tasks("conv123")

        assert len(tasks) == 1
        assert "goal" in tasks[0]
        assert "steps" in tasks[0]
        assert "result" in tasks[0]

    def test_empty_conversation_returns_empty_list(self):
        """Empty conversation should return empty list."""
        from src.skills.task_detector import TaskDetector

        detector = TaskDetector(db=MagicMock())
        detector.db.get_messages = MagicMock(return_value=[])

        tasks = detector.detect_tasks("conv123")

        assert tasks == []


class TestConstants:
    """Tests for class constants."""

    def test_topic_idle_hours_constant(self):
        """TOPIC_IDLE_HOURS should be 2.0."""
        from src.skills.task_detector import TaskDetector

        assert TaskDetector.TOPIC_IDLE_HOURS == 2.0

    def test_skill_min_chunks_constant(self):
        """SKILL_MIN_CHUNKS should be 6."""
        from src.skills.task_detector import TaskDetector

        assert TaskDetector.SKILL_MIN_CHUNKS == 6
