"""
Unit tests for SkillEvolver class.
"""

import pytest
import hashlib
from datetime import datetime


class TestSkillEvolverConstant:
    """Tests for SkillEvolver constants."""

    def test_skill_min_chunks_constant(self):
        """SKILL_MIN_CHUNKS should be 6."""
        from src.skills.evolver import SkillEvolver

        assert SkillEvolver.SKILL_MIN_CHUNKS == 6


class TestPassesRules:
    """Tests for _passes_rules method."""

    def test_filters_chitchat(self):
        """Should filter chitchat tasks."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "你好，聊聊天吧"}
        assert evolver._passes_rules(task) is False

    def test_filters_hello(self):
        """Should filter hello tasks."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "hello world"}
        assert evolver._passes_rules(task) is False

    def test_filters_thank_you(self):
        """Should filter thank you tasks."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "Thank you so much!"}
        assert evolver._passes_rules(task) is False

    def test_filters_hi(self):
        """Should filter hi tasks."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "Hi there!"}
        assert evolver._passes_rules(task) is False

    def test_filters_thanks(self):
        """Should filter thanks tasks."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "Thanks for your help"}
        assert evolver._passes_rules(task) is False

    def test_filters_chitchat_keyword(self):
        """Should filter chitchat keyword."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "chitchat about something"}
        assert evolver._passes_rules(task) is False

    def test_filters_small_talk(self):
        """Should filter small talk keyword."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "small talk session"}
        assert evolver._passes_rules(task) is False

    def test_filters_test(self):
        """Should filter test keyword."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "test the new feature"}
        assert evolver._passes_rules(task) is False

    def test_filters_bye(self):
        """Should filter bye keyword."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "再见"}
        assert evolver._passes_rules(task) is False

    def test_filters_weather(self):
        """Should filter weather keyword."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "今天天气怎么样"}
        assert evolver._passes_rules(task) is False

    def test_allows_technical_task(self):
        """Should allow technical task descriptions."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "Implement user authentication with JWT"}
        assert evolver._passes_rules(task) is True

    def test_allows_complex_task(self):
        """Should allow complex technical tasks."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "Optimize database query performance"}
        assert evolver._passes_rules(task) is True

    def test_case_insensitive_matching(self):
        """Should match keywords case-insensitively."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "HELLO there"}
        assert evolver._passes_rules(task) is False

        task2 = {"goal": "THANK You"}
        assert evolver._passes_rules(task2) is False

    def test_empty_goal(self):
        """Should allow empty goal (pass through)."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": ""}
        assert evolver._passes_rules(task) is True


class TestLLMEvaluate:
    """Tests for _llm_evaluate method."""

    def test_without_llm_returns_true(self):
        """Without LLM client should return True (pass through)."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None, llm_client=None)
        task = {"goal": "Do something"}
        assert evolver._llm_evaluate(task) is True

    def test_llm_returns_yes(self):
        """LLM returns YES should result in True."""
        from src.skills.evolver import SkillEvolver
        from src.llm_client import MockLLMClient

        mock_llm = MockLLMClient(response="YES")
        evolver = SkillEvolver(db=None, llm_client=mock_llm)
        task = {"goal": "Implement auth"}
        assert evolver._llm_evaluate(task) is True

    def test_llm_returns_no(self):
        """LLM returns NO should result in False."""
        from src.skills.evolver import SkillEvolver
        from src.llm_client import MockLLMClient

        mock_llm = MockLLMClient(response="NO")
        evolver = SkillEvolver(db=None, llm_client=mock_llm)
        task = {"goal": "Hello there"}
        assert evolver._llm_evaluate(task) is False

    def test_llm_failure_returns_false(self):
        """LLM failure should return False (reject)."""
        from src.skills.evolver import SkillEvolver

        class FailingLLM:
            def generate(self, prompt, **kwargs):
                raise Exception("LLM failed")

        evolver = SkillEvolver(db=None, llm_client=FailingLLM())
        task = {"goal": "Implement auth"}
        assert evolver._llm_evaluate(task) is False

    def test_case_insensitive_yes(self):
        """YES in any case should be accepted."""
        from src.skills.evolver import SkillEvolver
        from src.llm_client import MockLLMClient

        mock_llm = MockLLMClient(response="yes")
        evolver = SkillEvolver(db=None, llm_client=mock_llm)
        task = {"goal": "Technical task"}
        assert evolver._llm_evaluate(task) is True


class TestGenerateSkillMd:
    """Tests for _generate_skill_md method."""

    def test_with_llm_generates_skill_md(self):
        """With LLM should generate SKILL.md format."""
        from src.skills.evolver import SkillEvolver
        from src.llm_client import MockLLMClient

        mock_llm = MockLLMClient(response="# Test Skill\n## 目标\nTest")
        evolver = SkillEvolver(db=None, llm_client=mock_llm)
        task = {"goal": "Test skill", "steps": ["step1"], "result": "done"}
        result = evolver._generate_skill_md(task)
        assert result is not None
        assert "#" in result

    def test_without_llm_uses_template(self):
        """Without LLM should use template fallback."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None, llm_client=None)
        task = {
            "goal": "Test goal",
            "steps": ["step1", "step2"],
            "result": "Test result",
        }
        result = evolver._generate_skill_md(task)
        assert result is not None
        assert "## 目标" in result
        assert "## 步骤" in result
        assert "## 警告" in result

    def test_template_includes_goal(self):
        """Template should include goal."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None, llm_client=None)
        task = {"goal": "My custom goal", "steps": [], "result": ""}
        result = evolver._generate_skill_md(task)
        assert "My custom goal" in result

    def test_template_includes_steps(self):
        """Template should include steps."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None, llm_client=None)
        task = {"goal": "Goal", "steps": ["step1", "step2"], "result": ""}
        result = evolver._generate_skill_md(task)
        assert "1. step1" in result
        assert "2. step2" in result

    def test_template_includes_warnings_section(self):
        """Template should include warnings section."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None, llm_client=None)
        task = {"goal": "Goal", "steps": [], "result": ""}
        result = evolver._generate_skill_md(task)
        assert "## 警告" in result

    def test_llm_failure_uses_template(self):
        """LLM failure should fall back to template."""
        from src.skills.evolver import SkillEvolver

        class FailingLLM:
            def generate(self, prompt, **kwargs):
                raise Exception("LLM failed")

        evolver = SkillEvolver(db=None, llm_client=FailingLLM())
        task = {"goal": "Goal", "steps": ["step1"], "result": ""}
        result = evolver._generate_skill_md(task)
        assert "## 目标" in result


class TestScoreQuality:
    """Tests for _score_quality method."""

    def test_steps_above_2_adds_03(self):
        """Steps >= 2 should add 0.3."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "Goal", "steps": ["s1", "s2"], "result": ""}
        skill_md = "# Test"
        score = evolver._score_quality(task, skill_md)
        assert score >= 0.3

    def test_single_step_no_points(self):
        """Single step should not get step points."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "Goal", "steps": ["only_one"], "result": ""}
        skill_md = "# Test"
        score = evolver._score_quality(task, skill_md)
        assert score < 0.3

    def test_result_over_20_chars_adds_02(self):
        """Result > 20 chars should add 0.2."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "Goal", "steps": [], "result": "x" * 25}
        skill_md = "# Test"
        score = evolver._score_quality(task, skill_md)
        assert score >= 0.2

    def test_short_result_no_points(self):
        """Short result should not get points."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "Goal", "steps": [], "result": "short"}
        skill_md = "# Test"
        score = evolver._score_quality(task, skill_md)
        assert score < 0.2

    def test_content_over_200_chars_adds_02(self):
        """Content > 200 chars should add 0.2."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "Goal", "steps": [], "result": ""}
        skill_md = "# Test\n" + "x" * 250
        score = evolver._score_quality(task, skill_md)
        assert score >= 0.2

    def test_code_block_adds_015(self):
        """Code block should add 0.15."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "Goal", "steps": [], "result": ""}
        skill_md = "# Test\n```bash\necho hi\n```"
        score = evolver._score_quality(task, skill_md)
        assert score >= 0.15

    def test_warnings_section_adds_015(self):
        """Warnings section should add 0.15."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "Goal", "steps": [], "result": ""}
        skill_md = "# Test\n## 警告\n- warning1"
        score = evolver._score_quality(task, skill_md)
        assert score >= 0.15

    def test_warnings_english_adds_015(self):
        """English Warnings section should add 0.15."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "Goal", "steps": [], "result": ""}
        skill_md = "# Test\n## Warnings\n- warning1"
        score = evolver._score_quality(task, skill_md)
        assert score >= 0.15

    def test_max_score_is_1(self):
        """Max score should be 1.0."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "Goal", "steps": ["s1", "s2", "s3"], "result": "x" * 25}
        skill_md = "# Test\n" + "x" * 250 + "\n```bash\necho\n```\n## 警告\n- w"
        score = evolver._score_quality(task, skill_md)
        assert score == 1.0


class TestSaveSkill:
    """Tests for _save_skill method."""

    def test_generates_deterministic_skill_id(self, temp_db):
        """Should generate deterministic skill_id from SHA-256."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=temp_db)
        task = {"goal": "Test skill", "steps": [], "result": ""}
        skill_md = "# Test"
        quality = 0.5

        skill_id1 = evolver._save_skill(task, skill_md, quality, "conv1", "owner1")
        skill_id2 = evolver._save_skill(task, skill_md, quality, "conv1", "owner1")

        assert skill_id1 == skill_id2

    def test_skill_id_format(self, temp_db):
        """Skill_id should start with skill_ prefix."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=temp_db)
        task = {"goal": "Test skill", "steps": [], "result": ""}
        skill_md = "# Test"

        skill_id = evolver._save_skill(task, skill_md, 0.5, "conv1", "owner1")
        assert skill_id.startswith("skill_")

    def test_saves_skill_to_database(self, temp_db):
        """Should save skill to database."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=temp_db)
        task = {"goal": "Database test skill", "steps": [], "result": ""}
        skill_md = "# Test"

        skill_id = evolver._save_skill(task, skill_md, 0.5, "conv1", "owner1")

        saved = temp_db.get_skill(skill_id)
        assert saved is not None
        assert saved["skill_id"] == skill_id

    def test_saves_skill_version(self, temp_db):
        """Should save skill version."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=temp_db)
        task = {"goal": "Version test skill", "steps": [], "result": ""}
        skill_md = "# Test version skill"

        skill_id = evolver._save_skill(task, skill_md, 0.7, "conv2", "owner1")

        temp_db.cursor.execute(
            "SELECT * FROM skill_versions WHERE skill_id = ?", (skill_id,)
        )
        version = temp_db.cursor.fetchone()
        assert version is not None

    def test_associates_task_with_skill(self, temp_db):
        """Should associate task with skill."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=temp_db)
        task = {"goal": "Association test", "steps": [], "result": ""}
        skill_md = "# Test"

        skill_id = evolver._save_skill(task, skill_md, 0.5, "conv_task", "owner1")

        temp_db.cursor.execute(
            "SELECT * FROM task_skills WHERE task_id = ? AND skill_id = ?",
            ("conv_task", skill_id),
        )
        association = temp_db.cursor.fetchone()
        assert association is not None


class TestEvaluateAndGenerate:
    """Tests for evaluate_and_generate method."""

    def test_filtered_tasks_return_none(self):
        """Filtered tasks should return None."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=None)
        task = {"goal": "Hello there"}

        result = evolver.evaluate_and_generate(task, "conv1")
        assert result is None

    def test_llm_rejected_tasks_return_none(self):
        """LLM rejected tasks should return None."""
        from src.skills.evolver import SkillEvolver
        from src.llm_client import MockLLMClient

        mock_llm = MockLLMClient(response="NO")
        evolver = SkillEvolver(db=None, llm_client=mock_llm)
        task = {"goal": "Technical task but LLM says NO"}

        result = evolver.evaluate_and_generate(task, "conv1")
        assert result is None

    def test_valid_tasks_return_skill_id(self, temp_db):
        """Valid tasks should return skill_id."""
        from src.skills.evolver import SkillEvolver

        evolver = SkillEvolver(db=temp_db)
        task = {
            "goal": "Valid technical task",
            "steps": ["step1", "step2"],
            "result": "Completed successfully",
        }

        result = evolver.evaluate_and_generate(task, "conv_valid", "owner1")
        assert result is not None
        assert result.startswith("skill_")

    def test_full_pipeline(self, temp_db):
        """Full pipeline should: filter -> evaluate -> generate -> score -> save."""
        from src.skills.evolver import SkillEvolver

        class SmartMockLLM:
            def __init__(self):
                self.calls = []

            def generate(self, prompt, **kwargs):
                self.calls.append(prompt)
                if "YES" in prompt or "NO" in prompt:
                    return "YES"
                return "# Complete Pipeline\n## 目标\nTest\n## 步骤\n1. step1\n2. step2\n## 警告\n- ok"

        mock_llm = SmartMockLLM()
        evolver = SkillEvolver(db=temp_db, llm_client=mock_llm)
        task = {
            "goal": "Complete pipeline execution",
            "steps": ["step1", "step2"],
            "result": "x" * 30,
        }

        skill_id = evolver.evaluate_and_generate(task, "conv_pipeline", "owner1")

        assert skill_id is not None

        saved = temp_db.get_skill(skill_id)
        assert saved is not None
        assert saved["name"] == "Complete pipeline execution"

        temp_db.cursor.execute(
            "SELECT * FROM skill_versions WHERE skill_id = ?", (skill_id,)
        )
        version = temp_db.cursor.fetchone()
        assert version is not None

        temp_db.cursor.execute(
            "SELECT * FROM task_skills WHERE task_id = ?", ("conv_pipeline",)
        )
        assoc = temp_db.cursor.fetchone()
        assert assoc is not None

    def test_default_owner(self, temp_db):
        """Should use 'default' owner if not specified."""
        from src.skills.evolver import SkillEvolver

        class SmartMockLLM:
            def __init__(self):
                self.calls = []

            def generate(self, prompt, **kwargs):
                self.calls.append(prompt)
                if "YES" in prompt or "NO" in prompt:
                    return "YES"
                return "# Owner Skill\n## 目标\nTest\n## 步骤\n1. step1"

        mock_llm = SmartMockLLM()
        evolver = SkillEvolver(db=temp_db, llm_client=mock_llm)
        task = {"goal": "Owner skill creation", "steps": [], "result": ""}

        skill_id = evolver.evaluate_and_generate(task, "conv_owner")

        saved = temp_db.get_skill(skill_id)
        assert saved["owner"] == "default"
