#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for BatchImporter (src/pipeline/batch_importer.py)."""

import json
import os
import tempfile

import pytest

from src.pipeline.batch_importer import BatchImporter

# ---------- fixtures ----------


@pytest.fixture
def tmp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def importer(tmp_db_path):
    bi = BatchImporter(tmp_db_path)
    yield bi
    bi.close()


# ---------- JSON import ----------


class TestImportFromJson:
    def test_single_conversation_dict(self, importer, tmp_db_path):
        data = {
            "conversationId": "c_json_1",
            "messages": [
                {"id": "m1", "role": "user", "content": "hi", "timestamp": "2026-06-12T10:00:00Z"},
                {
                    "id": "m2",
                    "role": "assistant",
                    "content": "hello",
                    "timestamp": "2026-06-12T10:01:00Z",
                },
            ],
        }
        path = tmp_db_path + ".json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        result = importer.import_from_json(path)
        os.unlink(path)
        # Result has stats keys
        assert isinstance(result, dict)
        # 2 messages imported
        assert result.get("imported_messages", 0) >= 2

    def test_list_of_conversations(self, importer):
        data = [
            {
                "conversationId": "c_list_1",
                "messages": [
                    {
                        "id": "m1",
                        "role": "user",
                        "content": "hello",
                        "timestamp": "2026-06-12T10:00:00Z",
                    },
                ],
            },
            {
                "conversationId": "c_list_2",
                "messages": [
                    {
                        "id": "m2",
                        "role": "user",
                        "content": "world",
                        "timestamp": "2026-06-12T10:00:00Z",
                    },
                    {
                        "id": "m3",
                        "role": "user",
                        "content": "world 2",
                        "timestamp": "2026-06-12T10:01:00Z",
                    },
                ],
            },
        ]
        path = tempfile.mktemp(suffix=".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        result = importer.import_from_json(path)
        os.unlink(path)
        # 3 messages across 2 conversations
        assert result.get("imported_messages", 0) >= 3
        assert result.get("total_conversations", 0) >= 2

    def test_empty_messages_list(self, importer):
        data = {"conversationId": "c_empty", "messages": []}
        path = tempfile.mktemp(suffix=".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        result = importer.import_from_json(path)
        os.unlink(path)
        # No messages, but the import should still succeed
        assert isinstance(result, dict)

    def test_custom_field_names(self, importer):
        # Using 'conv_id' and 'turns' instead of defaults
        data = {
            "conv_id": "c_custom_1",
            "turns": [
                {
                    "id": "m1",
                    "role": "user",
                    "content": "test",
                    "timestamp": "2026-06-12T10:00:00Z",
                },
            ],
        }
        path = tempfile.mktemp(suffix=".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        result = importer.import_from_json(
            path, conversation_id_field="conv_id", messages_field="turns"
        )
        os.unlink(path)
        assert result.get("imported_messages", 0) >= 1

    def test_invalid_json_format_raises(self, importer):
        path = tempfile.mktemp(suffix=".json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("not a json string at all")
        with pytest.raises(Exception):
            importer.import_from_json(path)
        os.unlink(path)

    def test_json_with_unicode_content(self, importer):
        data = {
            "conversationId": "c_unicode",
            "messages": [
                {
                    "id": "m1",
                    "role": "user",
                    "content": "你好世界 🦞",
                    "timestamp": "2026-06-12T10:00:00Z",
                },
            ],
        }
        path = tempfile.mktemp(suffix=".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        result = importer.import_from_json(path)
        os.unlink(path)
        assert result.get("imported_messages", 0) >= 1


# ---------- CSV import ----------


class TestImportFromCsv:
    def test_basic_csv(self, importer):
        import csv as csvmod

        path = tempfile.mktemp(suffix=".csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csvmod.DictWriter(f, fieldnames=["conversation_id", "role", "content", "timestamp"])
            w.writeheader()
            w.writerow(
                {
                    "conversation_id": "c_csv_1",
                    "role": "user",
                    "content": "hi",
                    "timestamp": "2026-06-12T10:00:00Z",
                }
            )
            w.writerow(
                {
                    "conversation_id": "c_csv_1",
                    "role": "assistant",
                    "content": "hello",
                    "timestamp": "2026-06-12T10:01:00Z",
                }
            )
        result = importer.import_from_csv(path)
        os.unlink(path)
        assert isinstance(result, dict)
        assert result.get("imported_messages", 0) >= 2

    def test_csv_groups_by_conversation(self, importer):
        import csv as csvmod

        path = tempfile.mktemp(suffix=".csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csvmod.DictWriter(f, fieldnames=["conversation_id", "role", "content", "timestamp"])
            w.writeheader()
            w.writerow(
                {
                    "conversation_id": "cA",
                    "role": "user",
                    "content": "a1",
                    "timestamp": "2026-06-12T10:00:00Z",
                }
            )
            w.writerow(
                {
                    "conversation_id": "cB",
                    "role": "user",
                    "content": "b1",
                    "timestamp": "2026-06-12T10:00:00Z",
                }
            )
            w.writerow(
                {
                    "conversation_id": "cA",
                    "role": "user",
                    "content": "a2",
                    "timestamp": "2026-06-12T10:01:00Z",
                }
            )
        result = importer.import_from_csv(path)
        os.unlink(path)
        # 3 rows total, grouped into 2 conversations
        assert result.get("imported_messages", 0) >= 3
        assert result.get("total_conversations", 0) >= 2

    def test_csv_with_unicode(self, importer):
        import csv as csvmod

        path = tempfile.mktemp(suffix=".csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csvmod.DictWriter(f, fieldnames=["conversation_id", "role", "content", "timestamp"])
            w.writeheader()
            w.writerow(
                {
                    "conversation_id": "c_unicode",
                    "role": "user",
                    "content": "你好",
                    "timestamp": "2026-06-12T10:00:00Z",
                }
            )
        result = importer.import_from_csv(path)
        os.unlink(path)
        assert result.get("imported_messages", 0) >= 1

    def test_csv_with_custom_field_names(self, importer):
        import csv as csvmod

        path = tempfile.mktemp(suffix=".csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csvmod.DictWriter(f, fieldnames=["cid", "speaker", "text", "ts"])
            w.writeheader()
            w.writerow(
                {"cid": "c1", "speaker": "user", "text": "hello", "ts": "2026-06-12T10:00:00Z"}
            )
        result = importer.import_from_csv(
            path,
            conversation_id_field="cid",
            content_field="text",
            role_field="speaker",
            timestamp_field="ts",
        )
        os.unlink(path)
        assert result.get("imported_messages", 0) >= 1

    def test_csv_with_missing_optional_fields(self, importer):
        # No role -> defaults to 'user'; no timestamp -> now
        import csv as csvmod

        path = tempfile.mktemp(suffix=".csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csvmod.DictWriter(f, fieldnames=["conversation_id", "content"])
            w.writeheader()
            w.writerow({"conversation_id": "c1", "content": "no role no ts"})
        result = importer.import_from_csv(path)
        os.unlink(path)
        assert result.get("imported_messages", 0) >= 1

    def test_empty_csv(self, importer):
        import csv as csvmod

        path = tempfile.mktemp(suffix=".csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csvmod.DictWriter(f, fieldnames=["conversation_id", "content"])
            w.writeheader()
        result = importer.import_from_csv(path)
        os.unlink(path)
        assert isinstance(result, dict)


# ---------- stats dict ----------


class TestStats:
    def test_initial_stats(self, importer):
        assert importer.stats["total_conversations"] == 0
        assert importer.stats["total_messages"] == 0
        assert importer.stats["imported_messages"] == 0
        assert importer.stats["skipped_messages"] == 0
        assert importer.stats["errors"] == []

    def test_stats_after_import(self, importer):
        data = {
            "conversationId": "c_stats",
            "messages": [
                {"id": "m1", "role": "user", "content": "a", "timestamp": "2026-06-12T10:00:00Z"},
                {"id": "m2", "role": "user", "content": "b", "timestamp": "2026-06-12T10:01:00Z"},
            ],
        }
        path = tempfile.mktemp(suffix=".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        importer.import_from_json(path)
        os.unlink(path)
        # Stats updated
        assert importer.stats["imported_messages"] >= 2
        assert importer.stats["total_conversations"] >= 1
        assert importer.stats["total_messages"] >= 2


# ---------- close ----------


class TestClose:
    def test_close_releases_db(self, importer, tmp_db_path):
        importer.close()
        # After close, the importer should not be usable
        # (This is a smoke test — we just verify close() doesn't raise)
