"""Knowledge base ingestion — embeds documents and stores in Qdrant."""

from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.core.config import get_settings
from app.rag.embeddings import get_embeddings
from app.utils.file_processing import SUPPORTED_DOCUMENT_EXTENSIONS, extract_text_from_file

settings = get_settings()

_EMBEDDING_DIMS: dict[str, int] = {
    "mxbai-embed-large": 1024,
    "nomic-embed-text": 768,
    "all-minilm:l6-v2": 384,
}


def _get_embedding_dim() -> int:
    """Detect the embedding dimension for the configured model."""
    model = settings.ollama_embed_model
    if model in _EMBEDDING_DIMS:
        return _EMBEDDING_DIMS[model]
    emb = get_embeddings(model)
    return len(emb.embed_query("x"))


def _ensure_collection(client: QdrantClient):
    """Create the Qdrant collection if it doesn't exist."""
    collections = client.get_collections().collections
    if not any(c.name == settings.qdrant_collection for c in collections):
        dim = _get_embedding_dim()
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


# ── Multi-format text extraction ────────────────────────────────────────

# Text extraction functions moved to app.utils.file_processing
# Re-exported here for backward compatibility in ingest pipeline
_SUPPORTED_EXTENSIONS = SUPPORTED_DOCUMENT_EXTENSIONS
_extract_text = extract_text_from_file


# ── Ingestion ───────────────────────────────────────────────────────────


async def ingest_file(filepath: str | Path, doc_id: str | None = None) -> int:
    """Ingest a single file into Qdrant. Returns chunk count."""
    text = _extract_text(filepath)
    if not text.strip():
        return 0

    filename = Path(filepath).name

    splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
    chunks = splitter.split_text(text)

    client = QdrantClient(url=settings.qdrant_url)
    _ensure_collection(client)

    embeddings = get_embeddings()

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=settings.qdrant_collection,
        embedding=embeddings,
    )
    metadata: dict[str, str] = {"source": filename}
    if doc_id:
        metadata["doc_id"] = doc_id
    metadatas = [dict(metadata)] * len(chunks)
    vector_store.add_texts(chunks, metadatas=metadatas)
    return len(chunks)


async def ingest_all() -> int:
    """Ingest all supported files in the data directory. Returns total chunks."""
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    total = 0
    if not data_dir.exists():
        return 0

    for ext in _SUPPORTED_EXTENSIONS:
        for filepath in sorted(data_dir.glob(f"*{ext}")):
            total += await ingest_file(str(filepath))
    return total


if __name__ == "__main__":
    import asyncio
    total = asyncio.run(ingest_all())
    print(f"Ingested {total} chunks total.")
