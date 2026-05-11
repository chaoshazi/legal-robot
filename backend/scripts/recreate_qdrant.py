"""Drop and recreate the Qdrant collection, then re-ingest all data.

Run: python scripts/recreate_qdrant.py (from backend directory)

This is needed when switching to a different embedding model that produces
a different vector dimension (e.g. mxbai-embed-large 1024d → nomic-embed-text 768d).
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qdrant_client import QdrantClient
from app.core.config import get_settings
from app.rag.ingest import _get_embedding_dim, _ensure_collection


async def recreate():
    settings = get_settings()
    client = QdrantClient(url=settings.qdrant_url)

    # 1. Drop existing collection
    collections = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection in collections:
        print(f"Deleting collection '{settings.qdrant_collection}' ...")
        client.delete_collection(settings.qdrant_collection)
    else:
        print(f"Collection '{settings.qdrant_collection}' does not exist, skipping delete.")

    # 2. Create new collection with current model's dimension
    dim = _get_embedding_dim()
    print(f"Creating collection with {dim}-dim vectors (model: {settings.ollama_embed_model}) ...")
    _ensure_collection(client)

    # 3. Re-ingest
    from app.rag.ingest import ingest_all
    total = await ingest_all()
    print(f"Done — ingested {total} chunks.")


if __name__ == "__main__":
    asyncio.run(recreate())
