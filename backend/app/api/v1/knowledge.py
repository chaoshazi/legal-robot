import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.config import get_settings
from app.core.database import get_db
from app.models.knowledge import KnowledgeDocument
from app.models.user import User
from app.rag.ingest import _SUPPORTED_EXTENSIONS, ingest_file
from app.schemas.common import ApiResponse
from pydantic import BaseModel

router = APIRouter()
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


class DocumentInfo(BaseModel):
    id: str
    filename: str
    file_size: int
    chunk_count: int | None
    status: str
    error: str | None
    created_at: str


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}",
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    file_path = DATA_DIR / file.filename

    content = await file.read()
    file_path.write_bytes(content)

    doc = KnowledgeDocument(
        id=uuid.uuid4(),
        filename=file.filename,
        file_size=len(content),
        file_path=str(file_path),
        status="uploaded",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return ApiResponse(data=_doc_info(doc))


@router.get("/documents")
async def list_documents(
    current_user: User = Depends(require_role("admin", "lawyer")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
    )
    return ApiResponse(data=[_doc_info(d) for d in result.scalars().all()])


@router.post("/ingest/{doc_id}")
async def ingest_document(
    doc_id: str,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "uploaded":
        raise HTTPException(status_code=400, detail="Already ingested or in progress")

    doc.status = "ingesting"
    await db.commit()

    try:
        chunk_count = await ingest_file(doc.file_path, doc_id=str(doc.id))
        doc.status = "ingested"
        doc.chunk_count = chunk_count
    except Exception as e:
        doc.status = "failed"
        doc.error = str(e)
    await db.commit()
    await db.refresh(doc)

    return ApiResponse(data=_doc_info(doc))


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    await db.delete(doc)
    await db.commit()

    return ApiResponse(data=None)


def _doc_info(d: KnowledgeDocument) -> DocumentInfo:
    return DocumentInfo(
        id=str(d.id),
        filename=d.filename,
        file_size=d.file_size,
        chunk_count=d.chunk_count,
        status=d.status,
        error=d.error,
        created_at=d.created_at.isoformat() if d.created_at else "",
    )
