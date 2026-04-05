"""Unit tests for vector embedder module."""

import pytest
import numpy as np
import os
import tempfile
import struct


class TestNumpyOfflineEmbedder:
    """Tests for NumpyOfflineEmbedder class."""

    def test_is_available_returns_true(self):
        """is_available should return True for numpy offline embedder."""
        from src.vector.embedder import NumpyOfflineEmbedder

        embedder = NumpyOfflineEmbedder()
        assert embedder.is_available() is True

    def test_embed_returns_unit_norm_vector(self):
        """embed should return a unit-norm vector."""
        from src.vector.embedder import NumpyOfflineEmbedder

        embedder = NumpyOfflineEmbedder(seed=42)
        vec = embedder.embed("test text")
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 1e-6

    def test_embed_batch_returns_same_length(self):
        """embed_batch should return list of same length as input."""
        from src.vector.embedder import NumpyOfflineEmbedder

        embedder = NumpyOfflineEmbedder(seed=42)
        texts = ["text1", "text2", "text3"]
        results = embedder.embed_batch(texts)
        assert len(results) == 3

    def test_same_seed_returns_identical_vectors(self):
        """Two calls with same seed should return identical vectors."""
        from src.vector.embedder import NumpyOfflineEmbedder

        embedder1 = NumpyOfflineEmbedder(seed=42)
        embedder2 = NumpyOfflineEmbedder(seed=42)
        vec1 = embedder1.embed("same text")
        vec2 = embedder2.embed("same text")
        assert vec1 == vec2


class TestOpenAICompatibleEmbedder:
    """Tests for OpenAICompatibleEmbedder class."""

    def test_is_available_false_without_config(self):
        """is_available should return False when endpoint/api_key not set."""
        from src.vector.embedder import OpenAICompatibleEmbedder

        embedder = OpenAICompatibleEmbedder(endpoint=None, api_key=None)
        assert embedder.is_available() is False

    def test_is_available_true_with_config(self):
        """is_available should return True when endpoint and api_key are set."""
        from src.vector.embedder import OpenAICompatibleEmbedder

        embedder = OpenAICompatibleEmbedder(
            endpoint="http://localhost", api_key="test-key"
        )
        assert embedder.is_available() is True


class TestCreateEmbedder:
    """Tests for create_embedder factory function."""

    def test_falls_back_to_numpy_when_no_api_config(self):
        """Should fall back to NumpyOfflineEmbedder when no API config."""
        from src.vector.embedder import create_embedder, NumpyOfflineEmbedder

        embedder = create_embedder()
        assert isinstance(embedder, NumpyOfflineEmbedder)

    def test_returns_openai_when_api_configured(self, monkeypatch):
        """Should return OpenAICompatibleEmbedder when API is configured."""
        from src.vector.embedder import create_embedder, OpenAICompatibleEmbedder

        monkeypatch.setenv("LOBSTER_EMBED_ENDPOINT", "http://localhost:8080")
        monkeypatch.setenv("LOBSTER_EMBED_API_KEY", "test-key")
        embedder = create_embedder()
        assert isinstance(embedder, OpenAICompatibleEmbedder)


class TestSaveEmbedding:
    """Tests for save_embedding database method."""

    def test_save_and_retrieve_vector(self):
        """Should store and retrieve a vector BLOB."""
        from src.database import LobsterDatabase

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = LobsterDatabase(db_path)
            db.save_message(
                {
                    "id": "msg_test_emb",
                    "conversationId": "conv_test",
                    "seq": 1,
                    "role": "user",
                    "content": [{"type": "text", "text": "test"}],
                    "timestamp": "2024-01-01T00:00:00",
                }
            )
            vector = [0.1] * 1024
            chunk_id = db.save_embedding("message", "msg_test_emb", vector)
            assert chunk_id == "emb_message_msg_test_emb"
            db.close()
        finally:
            import os

            os.unlink(db_path)


class TestVectorSearch:
    """Tests for vector_search database method."""

    def test_returns_sorted_by_score_descending(self):
        """Should return results sorted by score descending."""
        from src.database import LobsterDatabase

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = LobsterDatabase(db_path)
            db.save_message(
                {
                    "id": "msg_v1",
                    "conversationId": "conv_vsearch",
                    "seq": 1,
                    "role": "user",
                    "content": [{"type": "text", "text": "test1"}],
                    "timestamp": "2024-01-01T00:00:00",
                }
            )
            vec1 = [1.0] + [0.0] * 1023
            vec2 = [0.0] * 1024
            vec2[0] = 0.5
            vec2[1] = 0.5
            db.save_embedding("message", "msg_v1", vec1)
            results = db.vector_search(vec1, top_k=20)
            assert len(results) >= 1
            assert results[0]["score"] >= results[-1]["score"]
            db.close()
        finally:
            import os

            os.unlink(db_path)

    def test_respects_top_k_limit(self):
        """Should respect top_k limit."""
        from src.database import LobsterDatabase

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = LobsterDatabase(db_path)
            for i in range(5):
                db.save_message(
                    {
                        "id": f"msg_topk_{i}",
                        "conversationId": "conv_topk",
                        "seq": i,
                        "role": "user",
                        "content": [{"type": "text", "text": f"test{i}"}],
                        "timestamp": "2024-01-01T00:00:00",
                    }
                )
                vec = [float(i)] + [0.0] * 1023
                db.save_embedding("message", f"msg_topk_{i}", vec)
            results = db.vector_search([1.0] + [0.0] * 1023, top_k=3)
            assert len(results) == 3
            db.close()
        finally:
            import os

            os.unlink(db_path)

    def test_returns_empty_for_zero_norm_query(self):
        """Should return empty list for zero-norm query."""
        from src.database import LobsterDatabase

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = LobsterDatabase(db_path)
            db.save_message(
                {
                    "id": "msg_zero",
                    "conversationId": "conv_zero",
                    "seq": 1,
                    "role": "user",
                    "content": [{"type": "text", "text": "test"}],
                    "timestamp": "2024-01-01T00:00:00",
                }
            )
            db.save_embedding("message", "msg_zero", [0.0] * 1024)
            results = db.vector_search([0.0] * 1024, top_k=20)
            assert results == []
            db.close()
        finally:
            import os

            os.unlink(db_path)
