"""Semantic cache for LLM responses.

Cache similar questions to reduce API calls and latency.
Uses embedding similarity to find cached responses.
"""

import hashlib
import logging
import time
from typing import Any

from langchain_core.embeddings import Embeddings

from app.core.metrics import (
    legal_bot_cache_hits_total,
    legal_bot_cache_misses_total,
    legal_bot_cache_size,
)

logger = logging.getLogger(__name__)

_CACHE_TTL = 3600  # 1 hour


class SemanticCache:
    """Simple in-memory semantic cache using embedding similarity with TTL."""

    def __init__(self, embeddings: Embeddings, threshold: float = 0.95):
        self._embeddings = embeddings
        self._threshold = threshold
        self._cache: dict[str, dict[str, Any]] = {}

    def get(self, question: str) -> dict[str, Any] | None:
        """Return cached response if a similar question exists."""
        self._evict_expired()
        embedding = self._embeddings.embed_query(question)
        for key, entry in list(self._cache.items()):
            similarity = self._cosine_similarity(embedding, entry["embedding"])
            if similarity >= self._threshold:
                legal_bot_cache_hits_total.inc()
                return entry["response"]
        legal_bot_cache_misses_total.inc()
        return None

    def set(self, question: str, response: dict[str, Any]):
        """Cache a response for future similar questions."""
        key = hashlib.sha256(question.encode()).hexdigest()
        self._cache[key] = {
            "embedding": self._embeddings.embed_query(question),
            "response": response,
            "ts": time.time(),
        }
        legal_bot_cache_size.inc()

    def _evict_expired(self):
        now = time.time()
        expired = [k for k, v in self._cache.items() if now - v.get("ts", 0) > _CACHE_TTL]
        for k in expired:
            del self._cache[k]
            legal_bot_cache_size.dec()

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def _is_cacheable(cfg: dict) -> bool:
    """Enable cache only when no tools, MCP, or knowledge are active.

    When external tools are in play the same query can produce different
    results (e.g., web search returns fresh data), so caching is unsafe.
    """
    active_tools = cfg.get("active_tool_ids", [])
    active_mcp = cfg.get("active_mcp_ids", [])
    active_knowledge = cfg.get("active_knowledge_ids", [])
    return not any([active_tools, active_mcp, active_knowledge])
