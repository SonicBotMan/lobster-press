#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for IntentExtractor (src/pipeline/intent_extractor.py)."""

import pytest

from src.pipeline.intent_extractor import IntentExtractor, Intent, Conclusion


def _msg(role, content):
    return {"role": role, "content": content}


class TestExtractIntents:
    def test_empty_messages_returns_empty_lists(self):
        ex = IntentExtractor()
        r = ex.extract_intents([])
        assert r["user_intents"] == []
        assert r["assistant_conclusions"] == []
        assert r["key_entities"] == []

    def test_question_intent_detected(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("user", "我们应该使用 PostgreSQL 吗？")])
        assert any(i.intent_type == "question" for i in r["user_intents"])

    def test_request_intent_detected(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("user", "帮我配置一下 OpenClaw 插件")])
        assert any(i.intent_type == "request" for i in r["user_intents"])

    def test_confirmation_intent_detected(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("user", "好的，可以。")])
        assert any(i.intent_type == "confirmation" for i in r["user_intents"])

    def test_complaint_intent_detected(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("user", "一直出现卡顿问题")])
        assert any(i.intent_type == "complaint" for i in r["user_intents"])

    def test_decision_conclusion_detected(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("assistant", "我们决定采用 PostgreSQL 作为主数据库")])
        assert any(c.conclusion_type == "decision" for c in r["assistant_conclusions"])

    def test_error_conclusion_detected(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("assistant", "编译错误：连接超时")])
        assert any(c.conclusion_type == "error" for c in r["assistant_conclusions"])

    def test_next_step_conclusion_detected(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("assistant", "下一步需要部署到生产环境")])
        assert any(c.conclusion_type == "next_step" for c in r["assistant_conclusions"])

    def test_result_conclusion_detected(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("assistant", "已经修复了这个问题")])
        assert any(c.conclusion_type == "result" for c in r["assistant_conclusions"])

    def test_user_intent_source_field(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("user", "怎么安装？")])
        assert all(i.source == "user" for i in r["user_intents"])

    def test_messages_with_empty_content_skipped(self):
        ex = IntentExtractor()
        msgs = [
            _msg("user", ""),
            _msg("user", "   "),
            _msg("assistant", ""),
            _msg("user", "帮我看看"),
        ]
        r = ex.extract_intents(msgs)
        assert any("帮我看看" in i.content for i in r["user_intents"])

    def test_string_content_with_blocks(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("user", "为什么选 PostgreSQL？")])
        assert any(i.intent_type == "question" for i in r["user_intents"])

    def test_block_content_text_block(self):
        ex = IntentExtractor()
        content = [
            {"type": "text", "text": "我们决定采用 PostgreSQL 方案"},
            {"type": "image", "url": "http://example.com/x.png"},
        ]
        r = ex.extract_intents([_msg("assistant", content)])
        assert any(c.conclusion_type == "decision" for c in r["assistant_conclusions"])

    def test_unknown_role_ignored(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("system", "这是一条系统消息，决定采用")])
        assert r["user_intents"] == []
        assert r["assistant_conclusions"] == []


class TestEntityExtraction:
    def test_version_number_extracted(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("user", "升级到 v4.0.94 后还是有问题")])
        # Both 'v4.0.94' and '4.0.94' match the version patterns.
        assert any(e in ("v4.0.94", "4.0.94") for e in r["key_entities"])

    def test_short_version_extracted(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("user", "使用 v4.0 版本")])
        assert any("v4.0" in e for e in r["key_entities"])

    def test_filename_extension_extracted(self):
        # Current implementation extracts just the file extension
        # (e.g. 'py') rather than the full filename. Document that.
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("user", "请检查 database.py 文件")])
        assert "py" in r["key_entities"]

    def test_path_extracted(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("user", "查看 src/database.py 路径")])
        assert any("/" in e for e in r["key_entities"])

    def test_top_entities_ranked_by_frequency(self):
        ex = IntentExtractor()
        # Use '1.0.0' (no 'v' prefix) so only the long pattern
        # \d+\.\d+\.\d+ matches — no ambiguity vs short patterns.
        msgs = [
            _msg("user", "1.0.0 有问题"),
            _msg("user", "1.0.0 又出现"),
            _msg("user", "1.0.0 重复"),
        ]
        r = ex.extract_intents(msgs)
        assert r["key_entities"][0] == "1.0.0"

    def test_key_entities_capped_at_ten(self):
        ex = IntentExtractor()
        parts = [f"v{i}.0.0" for i in range(20)]
        content = "我们看到了 " + " ".join(parts)
        r = ex.extract_intents([_msg("user", content)])
        assert len(r["key_entities"]) <= 10

    def test_no_entities_in_plain_text(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("user", "今天天气真好啊")])
        assert r["key_entities"] == []


class TestConfidence:
    def test_confidence_in_range_with_no_entities(self):
        ex = IntentExtractor()
        r = ex.extract_intents([_msg("user", "怎么配置？")])
        for i in r["user_intents"]:
            assert 0.7 <= i.confidence <= 1.0

    def test_confidence_increases_with_entities(self):
        ex = IntentExtractor()
        content = "帮我检查 v4.0.94 的 database.py 在 src/utils/tokens.py 的逻辑"
        r = ex.extract_intents([_msg("user", content)])
        assert r["user_intents"] != []
        max_conf = max(i.confidence for i in r["user_intents"])
        assert max_conf > 0.7

    def test_confidence_capped_at_one(self):
        ex = IntentExtractor()
        content = "检查 v4.0.94 database.py src/foo.py src/bar.py v3.0.0 v2.0.0"
        r = ex.extract_intents([_msg("user", content)])
        for i in r["user_intents"]:
            assert i.confidence <= 1.0


class TestDeduplication:
    def test_repeated_intent_key_deduped(self):
        ex = IntentExtractor()
        msgs = [
            _msg("user", "怎么配置？"),
            _msg("user", "怎么配置？"),
        ]
        r = ex.extract_intents(msgs)
        questions = [i for i in r["user_intents"] if i.intent_type == "question"]
        # Dedup is by (type, content[:50]); same content -> 1
        assert len(questions) == 1

    def test_same_type_different_content_both_kept(self):
        ex = IntentExtractor()
        msgs = [
            _msg("user", "怎么配置？"),
            _msg("user", "怎么部署？"),
        ]
        r = ex.extract_intents(msgs)
        questions = [i for i in r["user_intents"] if i.intent_type == "question"]
        assert len(questions) == 2


class TestDataclasses:
    def test_intent_fields(self):
        i = Intent(
            intent_type="question", content="x", confidence=0.9, source="user", entities=["a"]
        )
        assert i.intent_type == "question"
        assert i.content == "x"
        assert i.confidence == 0.9
        assert i.source == "user"
        assert i.entities == ["a"]

    def test_conclusion_fields(self):
        c = Conclusion(conclusion_type="decision", content="y", confidence=0.8, entities=["b"])
        assert c.conclusion_type == "decision"
        assert c.content == "y"
        assert c.confidence == 0.8
        assert c.entities == ["b"]

    def test_intent_default_entities_is_empty_list(self):
        i = Intent(intent_type="question", content="x", confidence=0.9, source="user")
        assert i.entities == []
