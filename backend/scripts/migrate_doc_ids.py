"""One-time migration: re-ingest all existing documents to add doc_id metadata
in Qdrant.  Needed after commit that added ``doc_id`` to ingestion metadata.

Usage::

    cd backend && python scripts/migrate_doc_ids.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure app package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.database import async_session
from app.models.knowledge import KnowledgeDocument
from app.rag.ingest import ingest_file


async def main():
    async with async_session() as db:
        result = await db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.status == "ingested")
        )
        docs = list(result.scalars().all())

    if not docs:
        print("No ingested documents to migrate.")
        return

    print(f"Found {len(docs)} ingested document(s). Re-ingesting...")
    for doc in docs:
        filepath = doc.file_path
        if not filepath or not Path(filepath).exists():
            print(f"  SKIP {doc.filename}: file not found at {filepath}")
            continue

        print(f"  Re-ingesting {doc.filename} ({doc.id})...", end=" ", flush=True)
        try:
            async with async_session() as db:
                # Reset status to uploaded so the DB constraint is happy
                result = await db.execute(
                    select(KnowledgeDocument).where(KnowledgeDocument.id == doc.id)
                )
                d = result.scalar_one_or_none()
                if d:
                    d.status = "uploaded"
                    await db.commit()

            chunk_count = await ingest_file(filepath, doc_id=str(doc.id))

            async with async_session() as db:
                result = await db.execute(
                    select(KnowledgeDocument).where(KnowledgeDocument.id == doc.id)
                )
                d = result.scalar_one_or_none()
                if d:
                    d.status = "ingested"
                    d.chunk_count = chunk_count
                    await db.commit()

            print(f"{chunk_count} chunks")
        except Exception as e:
            print(f"FAILED: {e}")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
