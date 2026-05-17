"""Hybrid retriever — dense vector search + keyword fallback for article numbers.

Dense embeddings alone struggle with exact article-number matching (e.g.
"第一千零九十一条").  When the query contains a legal article reference we
also search by exact substring match via Qdrant scroll and merge results.
"""

import re
from typing import Any

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.core.config import get_settings
from app.rag.embeddings import get_embeddings

settings = get_settings()

# Known embedding dimensions — avoids calling the model just to get dims
_EMBEDDING_DIMS: dict[str, int] = {
    "mxbai-embed-large": 1024,
    "nomic-embed-text": 768,
    "all-minilm:l6-v2": 384,
}

_COLLECTION_DIM: int | None = None


def _get_collection_dim() -> int:
    """Return the embedding dimension for the configured model."""
    global _COLLECTION_DIM
    if _COLLECTION_DIM is not None:
        return _COLLECTION_DIM
    model = settings.ollama_embed_model
    if model in _EMBEDDING_DIMS:
        _COLLECTION_DIM = _EMBEDDING_DIMS[model]
    else:
        # Unknown model — probe it
        emb = get_embeddings(model)
        _COLLECTION_DIM = len(emb.embed_query("x"))
    return _COLLECTION_DIM

# ── Article number extraction ─────────────────────────────────────────────

_CHINESE_DIGITS = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "十": 10, "百": 100, "千": 1000, "万": 10000,
}

# Combined pattern: "第X千X百X十X条" or "第X条" or "第1091条"
_ARTICLE_RE = re.compile(r"第[一-鿿\d]+条")


def _chinese_num_to_arabic(chinese: str) -> int:
    """Convert Chinese numeral string to integer.

    Handles scaled numbers like 一千零九十一 → 1091.
    """
    total = 0
    buf = 0
    for ch in chinese:
        val = _CHINESE_DIGITS.get(ch)
        if val is None:
            continue
        if val >= 10:
            buf = buf * val if buf else val
        else:
            buf += val
    return total + buf


def _article_to_search_tokens(article_ref: str) -> list[str]:
    """Normalise an article-number reference into one or more search tokens.

    Preserves the full form (with ``第``/``条``) because Qdrant's ``MatchText``
    does exact-token matching and Chinese tokens are not word-segmented.
    """
    return [article_ref]  # e.g. "第一千零九十一条"


def _extract_article_numbers(text: str) -> list[str]:
    """Extract unique article-number strings from query text."""
    return list(set(_ARTICLE_RE.findall(text)))


# ── Collection helpers ────────────────────────────────────────────────────


def _ensure_collection(client: QdrantClient):
    collections = client.get_collections().collections
    exists = any(c.name == settings.qdrant_collection for c in collections)

    if not exists:
        dim = _get_collection_dim()
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
    else:
        # Validate existing collection dimension matches the configured model
        info = client.get_collection(settings.qdrant_collection)
        existing_dim = info.config.params.vectors.size
        expected_dim = _get_collection_dim()
        if existing_dim != expected_dim:
            raise RuntimeError(
                f"Qdrant collection '{settings.qdrant_collection}' has {existing_dim}-dim vectors "
                f"but the configured embedding model produces {expected_dim}-dim vectors. "
                f"Recreate the collection with: python scripts/recreate_qdrant.py"
            )

    # Ensure full-text index on page_content for keyword search
    try:
        client.create_payload_index(
            collection_name=settings.qdrant_collection,
            field_name="page_content",
            field_type="text",
        )
    except Exception:
        pass  # index may already exist


def _build_vector_store():
    client = QdrantClient(url=settings.qdrant_url)
    _ensure_collection(client)
    embeddings = get_embeddings()
    return QdrantVectorStore(
        client=client,
        collection_name=settings.qdrant_collection,
        embedding=embeddings,
    )


# ── Hybrid retriever ──────────────────────────────────────────────────────


class HybridRetriever:
    """Retriever that runs dense vector search and keyword article-number
    search in parallel, then merges and deduplicates results."""

    def __init__(self, store: QdrantVectorStore, client: QdrantClient):
        self._store = store
        self._client = client
        self.search_kwargs: dict[str, Any] = {"k": 8}

    async def ainvoke(self, query: str, doc_ids: list[str] | None = None) -> list[Document]:
        """Search with optional ``doc_ids`` filter to restrict to specific documents."""
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue

        # Empty list = no KB selected, return no results
        if doc_ids is not None and not doc_ids:
            return []

        seen: set[str] = set()
        results: list[Document] = []

        # Build optional Qdrant filter
        qdrant_filter: Filter | None = None
        if doc_ids:
            qdrant_filter = Filter(
                should=[FieldCondition(key="metadata.doc_id", match=MatchValue(value=d)) for d in doc_ids],
            )

        # 1 — Dense vector search
        search_kw = dict(self.search_kwargs)
        if qdrant_filter is not None:
            search_kw["filter"] = qdrant_filter
        docs = await self._store.asimilarity_search(query, **search_kw)

        # Fallback: if doc_ids filter matched nothing, the Qdrant points likely
        # lack the "doc_id" field (legacy data).  Retry by source filename.
        if not docs and qdrant_filter is not None:
            source_filter = await self._build_source_filter(doc_ids)
            if source_filter:
                search_kw["filter"] = source_filter
                docs = await self._store.asimilarity_search(query, **search_kw)

        for d in docs:
            seen.add(d.page_content)
            results.append(d)

        # 2 — Keyword search for article numbers
        article_refs = _extract_article_numbers(query)
        for ref in article_refs:
            search_tokens = _article_to_search_tokens(ref)
            for token in search_tokens:
                keyword_docs = self._keyword_search(token, filter_extra=qdrant_filter)
                for d in keyword_docs:
                    if d.page_content not in seen:
                        seen.add(d.page_content)
                        results.append(d)

        # Keyword fallback: same as above — retry by source if doc_id filter matched nothing
        if not results and qdrant_filter is not None:
            source_filter = await self._build_source_filter(doc_ids)
            if source_filter:
                for ref in _extract_article_numbers(query):
                    for token in _article_to_search_tokens(ref):
                        for d in self._keyword_search(token, filter_extra=source_filter):
                            if d.page_content not in seen:
                                seen.add(d.page_content)
                                results.append(d)

        return results

    async def _build_source_filter(self, doc_ids: list[str] | None):
        """Fallback: build a filter by ``source`` filename for legacy data that
        lacks the ``doc_id`` metadata field."""
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue
        from app.core.database import async_session
        from app.models.knowledge import KnowledgeDocument
        from sqlalchemy import select

        try:
            async with async_session() as db:
                result = await db.execute(
                    select(KnowledgeDocument).where(KnowledgeDocument.id.in_(doc_ids))
                )
                filenames = [d.filename for d in result.scalars().all()]
        except Exception:
            return None

        if not filenames:
            return None
        return Filter(
            should=[FieldCondition(key="metadata.source", match=MatchValue(value=f)) for f in filenames],
        )

    def _keyword_search(self, token: str, filter_extra: Any | None = None) -> list[Document]:
        """Scroll points whose ``page_content`` contains *token*."""
        from qdrant_client.http.models import FieldCondition, Filter, MatchText

        try:
            conditions: list = [
                FieldCondition(
                    key="page_content",
                    match=MatchText(text=token),
                )
            ]
            scroll_filter = Filter(must=conditions)
            if filter_extra is not None:
                scroll_filter = Filter(must=conditions, should=filter_extra.should)
            scroll_result = self._client.scroll(
                collection_name=settings.qdrant_collection,
                limit=50,
                with_payload=True,
                scroll_filter=scroll_filter,
            )
        except Exception:
            return []

        docs: list[Document] = []
        for point in scroll_result[0]:
            payload = point.payload or {}
            docs.append(
                Document(
                    page_content=payload.get("page_content", ""),
                    metadata=payload.get("metadata", {}),
                )
            )
        return docs


# ── Global cache ──────────────────────────────────────────────────────────

_cached_store = None
_cached_client = None
_cached_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    """Build cached hybrid retriever (sync)."""
    global _cached_retriever, _cached_store, _cached_client
    if _cached_retriever is not None:
        return _cached_retriever

    client = QdrantClient(url=settings.qdrant_url)
    _ensure_collection(client)
    embeddings = get_embeddings()
    store = QdrantVectorStore(
        client=client,
        collection_name=settings.qdrant_collection,
        embedding=embeddings,
    )
    _cached_store = store
    _cached_client = client
    _cached_retriever = HybridRetriever(store, client)
    return _cached_retriever


async def async_get_retriever() -> HybridRetriever:
    """Build cached hybrid retriever (async), non-blocking on first build."""
    global _cached_retriever
    if _cached_retriever is not None:
        return _cached_retriever

    import asyncio
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, get_retriever)
    return _cached_retriever  # type: ignore[return-value]
