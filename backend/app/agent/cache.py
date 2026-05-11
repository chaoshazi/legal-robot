"""Semantic cache for LLM responses.

Cache similar questions to reduce API calls and latency.
Uses embedding similarity to find cached responses.
"""

import hashlib
from typing import Any

from langchain_core.embeddings import Embeddings


class SemanticCache:
    """Simple in-memory semantic cache using embedding similarity."""

    def __init__(self, embeddings: Embeddings, threshold: float = 0.95):
        self._embeddings = embeddings
        self._threshold = threshold
        self._cache: dict[str, dict[str, Any]] = {}

    def get(self, question: str) -> dict[str, Any] | None:
        """Return cached response if a similar question exists."""
        embedding = self._embeddings.embed_query(question)
        for key, entry in self._cache.items():
            similarity = self._cosine_similarity(embedding, entry["embedding"])
            if similarity >= self._threshold:
                return entry["response"]
        return None

    def set(self, question: str, response: dict[str, Any]):
        """Cache a response for future similar questions."""
        key = hashlib.sha256(question.encode()).hexdigest()
        self._cache[key] = {
            "embedding": self._embeddings.embed_query(question),
            "response": response,
        }

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
