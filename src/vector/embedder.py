"""Vector embedding module for lobster-press."""

import os
import numpy as np
import requests
from abc import ABC, abstractmethod
from typing import List

EMBEDDING_DIM = 1024


class BaseEmbedder(ABC):
    """Base class for vector embedding providers."""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the embedder is available."""
        pass


class OpenAICompatibleEmbedder(BaseEmbedder):
    """OpenAI compatible API embedder."""

    def __init__(
        self, endpoint: str = None, api_key: str = None, model: str = "bge-m3"
    ):
        self.endpoint = endpoint or os.environ.get("LOBSTER_EMBED_ENDPOINT")
        self.api_key = api_key or os.environ.get("LOBSTER_EMBED_API_KEY")
        self.model = model

    def is_available(self) -> bool:
        return bool(self.endpoint and self.api_key)

    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self.is_available():
            raise RuntimeError(
                "Embedder not available. Set LOBSTER_EMBED_ENDPOINT and LOBSTER_EMBED_API_KEY."
            )
        url = f"{self.endpoint}/embeddings"
        payload = {"model": self.model, "input": texts}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]


class NumpyOfflineEmbedder(BaseEmbedder):
    """Offline numpy-based embedder for testing/fallback."""

    def __init__(self, dim: int = EMBEDDING_DIM, seed: int = 42):
        self.dim = dim
        self.rng = np.random.default_rng(seed)

    def is_available(self) -> bool:
        return True

    def embed(self, text: str) -> List[float]:
        vec = self.rng.standard_normal(self.dim)
        norm = np.linalg.norm(vec)
        return (vec / norm).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]


def create_embedder(**kwargs) -> BaseEmbedder:
    """Factory function to create an embedder instance."""
    embedder = OpenAICompatibleEmbedder(**kwargs)
    if embedder.is_available():
        return embedder
    print("⚠️ Embedding API 不可用，降级为 numpy 离线向量")
    return NumpyOfflineEmbedder()
