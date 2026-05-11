"""Embedding model integration — connects to local Ollama."""

from functools import lru_cache

from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.embeddings import Embeddings

from app.core.config import get_settings

settings = get_settings()


class CachedOllamaEmbeddings(Embeddings):
    """Wrapper around OllamaEmbeddings with LRU cache for embed_query.

    Same query repeated (or rephrased) within a session skips the ~4s
    Ollama inference and returns the cached vector instantly.
    """

    def __init__(self, model: str | None = None):
        self._inner = OllamaEmbeddings(
            model=model or settings.ollama_embed_model,
            base_url=settings.ollama_base_url,
        )

    @lru_cache(maxsize=256)
    def _cached_query(self, query: str) -> list[float]:
        return self._inner.embed_query(query)

    def embed_query(self, text: str) -> list[float]:
        return self._cached_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._inner.embed_documents(texts)


def get_embeddings(model: str | None = None) -> Embeddings:
    """Return cached Ollama embedding instance.

    Available models on this host:
    - mxbai-embed-large (334M, best quality, ~4.4s per query)
    - nomic-embed-text (137M, balanced, ~2.1s per query)
    - all-minilm:l6-v2 (23M, lightweight, ~0.5s per query)
    """
    return CachedOllamaEmbeddings(model=model)
