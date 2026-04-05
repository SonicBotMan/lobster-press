"""
Unit tests for skill models and database operations.
"""

import pytest
import json
from datetime import datetime


class TestSkillDataclass:
    """Tests for Skill dataclass."""

    def test_import(self):
        """Should be able to import Skill."""
        from src.skills.models import Skill

        assert Skill is not None

    def test_to_dict_returns_all_fields(self):
        """to_dict should return all fields."""
        from src.skills.models import Skill

        skill = Skill(
            skill_id="skill_123",
            name="Test Skill",
            description="A test skill",
            owner="agent:001",
            visibility="public",
            quality_score=0.85,
            version=2,
            steps=["step1", "step2"],
            warnings=["warning1"],
            script="echo test",
            source_task_ids=["task_1", "task_2"],
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-02T00:00:00",
        )
        result = skill.to_dict()
        assert result["skill_id"] == "skill_123"
        assert result["name"] == "Test Skill"
        assert result["description"] == "A test skill"
        assert result["owner"] == "agent:001"
        assert result["visibility"] == "public"
        assert result["quality_score"] == 0.85
        assert result["version"] == 2
        assert result["steps"] == ["step1", "step2"]
        assert result["warnings"] == ["warning1"]
        assert result["script"] == "echo test"
        assert result["source_task_ids"] == ["task_1", "task_2"]
        assert result["created_at"] == "2026-01-01T00:00:00"
        assert result["updated_at"] == "2026-01-02T00:00:00"

    def test_default_values(self):
        """Should have correct default values."""
        from src.skills.models import Skill

        skill = Skill(skill_id="skill_456", name="Minimal Skill")
        assert skill.skill_id == "skill_456"
        assert skill.name == "Minimal Skill"
        assert skill.description == ""
        assert skill.owner == "default"
        assert skill.visibility == "private"
        assert skill.quality_score == 0.0
        assert skill.version == 1
        assert skill.steps == []
        assert skill.warnings == []
        assert skill.script == ""
        assert skill.source_task_ids == []
        assert skill.created_at == ""
        assert skill.updated_at == ""

    def test_create_with_all_fields(self):
        """Should create skill with all fields specified."""
        from src.skills.models import Skill

        skill = Skill(
            skill_id="skill_full",
            name="Full Skill",
            description="Full description",
            owner="agent:test",
            visibility="public",
            quality_score=1.0,
            version=5,
            steps=["s1", "s2", "s3"],
            warnings=["w1", "w2"],
            script="python test.py",
            source_task_ids=["t1"],
            created_at="2026-03-01T00:00:00",
            updated_at="2026-03-02T00:00:00",
        )
        assert skill.skill_id == "skill_full"
        assert skill.name == "Full Skill"
        assert len(skill.steps) == 3
        assert len(skill.warnings) == 2


class TestTaskSummaryDataclass:
    """Tests for TaskSummary dataclass."""

    def test_import(self):
        """Should be able to import TaskSummary."""
        from src.skills.models import TaskSummary

        assert TaskSummary is not None

    def test_to_dict_returns_all_fields(self):
        """to_dict should return all fields."""
        from src.skills.models import TaskSummary

        ts = TaskSummary(
            task_id="task_123",
            conversation_id="conv_456",
            owner="agent:001",
            goal="Complete the task",
            steps=["step1", "step2"],
            result="Task completed",
            status="completed",
            created_at="2026-01-01T00:00:00",
            skill_generated=True,
        )
        result = ts.to_dict()
        assert result["task_id"] == "task_123"
        assert result["conversation_id"] == "conv_456"
        assert result["owner"] == "agent:001"
        assert result["goal"] == "Complete the task"
        assert result["steps"] == ["step1", "step2"]
        assert result["result"] == "Task completed"
        assert result["status"] == "completed"
        assert result["created_at"] == "2026-01-01T00:00:00"
        assert result["skill_generated"] is True

    def test_default_values(self):
        """Should have correct default values."""
        from src.skills.models import TaskSummary

        ts = TaskSummary(task_id="task_default", conversation_id="conv_default")
        assert ts.task_id == "task_default"
        assert ts.conversation_id == "conv_default"
        assert ts.owner == "default"
        assert ts.goal == ""
        assert ts.steps == []
        assert ts.result == ""
        assert ts.status == "completed"
        assert ts.created_at == ""
        assert ts.skill_generated is False


class TestDatabaseSkillTables:
    """Integration tests for skill tables in database."""

    def test_skills_table_created(self, temp_db):
        """skills table should be created correctly."""
        temp_db.cursor.execute("""
            SELECT name, type FROM sqlite_master 
            WHERE type='table' AND name='skills'
        """)
        result = temp_db.cursor.fetchone()
        assert result is not None
        assert result[0] == "skills"

    def test_skill_versions_table_created(self, temp_db):
        """skill_versions table should be created correctly."""
        temp_db.cursor.execute("""
            SELECT name, type FROM sqlite_master 
            WHERE type='table' AND name='skill_versions'
        """)
        result = temp_db.cursor.fetchone()
        assert result is not None
        assert result[0] == "skill_versions"

    def test_task_skills_table_created(self, temp_db):
        """task_skills table should be created correctly."""
        temp_db.cursor.execute("""
            SELECT name, type FROM sqlite_master 
            WHERE type='table' AND name='task_skills'
        """)
        result = temp_db.cursor.fetchone()
        assert result is not None
        assert result[0] == "task_skills"

    def test_skills_fts_virtual_table_created(self, temp_db):
        """skills_fts virtual table should be created."""
        temp_db.cursor.execute("""
            SELECT name, type FROM sqlite_master 
            WHERE type='table' AND name='skills_fts'
        """)
        result = temp_db.cursor.fetchone()
        assert result is not None

    def test_skills_indexes_created(self, temp_db):
        """Skills indexes should be created."""
        temp_db.cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_skills_owner'
        """)
        assert temp_db.cursor.fetchone() is not None

        temp_db.cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_skill_versions'
        """)
        assert temp_db.cursor.fetchone() is not None


class TestSaveSkill:
    """Tests for save_skill method."""

    def test_save_skill_returns_skill_id(self, temp_db):
        """save_skill should return skill_id."""
        from src.skills.models import Skill

        skill = Skill(
            skill_id="skill_save_001",
            name="Save Test Skill",
            description="Testing save method",
        )
        result = temp_db.save_skill(skill)
        assert result == "skill_save_001"

    def test_save_and_retrieve_skill(self, temp_db):
        """Saved skill should be retrievable."""
        from src.skills.models import Skill

        skill = Skill(
            skill_id="skill_save_002",
            name="Retrieve Test Skill",
            description="Testing retrieve",
            owner="agent:test",
            visibility="public",
            quality_score=0.75,
            steps=["step1", "step2"],
            warnings=["warn1"],
            script="test.sh",
            source_task_ids=["task_1"],
        )
        temp_db.save_skill(skill)

        result = temp_db.get_skill("skill_save_002")
        assert result is not None
        assert result["skill_id"] == "skill_save_002"
        assert result["name"] == "Retrieve Test Skill"
        assert result["description"] == "Testing retrieve"
        assert result["owner"] == "agent:test"
        assert result["visibility"] == "public"
        assert result["quality_score"] == 0.75


class TestGetSkill:
    """Tests for get_skill method."""

    def test_get_skill_returns_dict_when_exists(self, temp_db):
        """get_skill should return skill dict when exists."""
        from src.skills.models import Skill

        skill = Skill(skill_id="skill_get_001", name="Get Test Skill")
        temp_db.save_skill(skill)

        result = temp_db.get_skill("skill_get_001")
        assert result is not None
        assert isinstance(result, dict)
        assert result["skill_id"] == "skill_get_001"

    def test_get_skill_returns_none_when_not_exists(self, temp_db):
        """get_skill should return None when not exists."""
        result = temp_db.get_skill("nonexistent_skill")
        assert result is None


class TestSearchSkills:
    """Tests for search_skills method."""

    def test_full_query_returns_all_skills(self, temp_db):
        """query='*' should return all skills."""
        from src.skills.models import Skill

        skill1 = Skill(skill_id="skill_search_001", name="Python Skill")
        skill2 = Skill(skill_id="skill_search_002", name="JavaScript Skill")
        temp_db.save_skill(skill1)
        temp_db.save_skill(skill2)

        results = temp_db.search_skills("*")
        assert len(results) >= 2

    def test_keyword_query_uses_fts5(self, temp_db):
        """Keyword query should use FTS5."""
        from src.skills.models import Skill

        skill = Skill(
            skill_id="skill_search_003",
            name="Database Optimization",
            description="PostgreSQL tuning",
        )
        temp_db.save_skill(skill)

        results = temp_db.search_skills("Database")
        assert isinstance(results, list)

    def test_filter_by_owner(self, temp_db):
        """Should filter by owner."""
        from src.skills.models import Skill

        skill = Skill(
            skill_id="skill_search_004",
            name="Owner Filter Test",
            owner="agent:filter_test",
        )
        temp_db.save_skill(skill)

        results = temp_db.search_skills("*", owner="agent:filter_test")
        assert all(r["owner"] == "agent:filter_test" for r in results)

    def test_filter_by_visibility(self, temp_db):
        """Should filter by visibility."""
        from src.skills.models import Skill

        skill = Skill(
            skill_id="skill_search_005", name="Visibility Test", visibility="public"
        )
        temp_db.save_skill(skill)

        results = temp_db.search_skills("*", visibility="public")
        assert all(r["visibility"] == "public" for r in results)


class TestGetSkillsByOwner:
    """Tests for get_skills_by_owner method."""

    def test_returns_owners_skills(self, temp_db):
        """Should return skills belonging to owner."""
        from src.skills.models import Skill

        skill = Skill(
            skill_id="skill_owner_001", name="Owner Test", owner="agent:owner_test"
        )
        temp_db.save_skill(skill)

        results = temp_db.get_skills_by_owner("agent:owner_test", include_public=False)
        assert any(r["skill_id"] == "skill_owner_001" for r in results)

    def test_include_public_true(self, temp_db):
        """include_public=True should include public skills."""
        from src.skills.models import Skill

        skill = Skill(
            skill_id="skill_public_001", name="Public Skill", visibility="public"
        )
        temp_db.save_skill(skill)

        results = temp_db.get_skills_by_owner("agent:other", include_public=True)
        assert any(r["visibility"] == "public" for r in results)

    def test_include_public_false(self, temp_db):
        """include_public=False should exclude public skills."""
        from src.skills.models import Skill

        Skill(
            skill_id="skill_public_002",
            name="Public Skill 2",
            owner="agent:someone_else",
            visibility="public",
        )
        temp_db.save_skill(
            Skill(
                skill_id="skill_public_002",
                name="Public Skill 2",
                owner="agent:someone_else",
                visibility="public",
            )
        )

        results = temp_db.get_skills_by_owner("agent:other", include_public=False)
        assert not any(r["skill_id"] == "skill_public_002" for r in results)


class TestSaveTaskSkill:
    """Tests for save_task_skill method."""

    def test_creates_association(self, temp_db):
        """Should create task-skill association."""
        from src.skills.models import Skill

        temp_db.save_skill(Skill(skill_id="skill_task_001", name="Task Skill"))

        temp_db.save_task_skill("task_001", "skill_task_001")

        temp_db.cursor.execute(
            "SELECT * FROM task_skills WHERE task_id='task_001' AND skill_id='skill_task_001'"
        )
        result = temp_db.cursor.fetchone()
        assert result is not None

    def test_duplicate_ignored(self, temp_db):
        """Duplicate association should be ignored (INSERT OR IGNORE)."""
        from src.skills.models import Skill

        temp_db.save_skill(Skill(skill_id="skill_task_002", name="Task Skill 2"))

        temp_db.save_task_skill("task_002", "skill_task_002")
        temp_db.save_task_skill("task_002", "skill_task_002")

        temp_db.cursor.execute(
            "SELECT COUNT(*) FROM task_skills WHERE task_id='task_002' AND skill_id='skill_task_002'"
        )
        count = temp_db.cursor.fetchone()[0]
        assert count == 1
