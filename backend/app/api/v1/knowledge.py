import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_role
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models.knowledge import KnowledgeDocument
from app.models.user import User
from app.rag.ingest import _SUPPORTED_EXTENSIONS, ingest_file
from app.schemas.common import ApiResponse
from app.services.audit import log_audit
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
    await log_audit(
        user_id=str(current_user.id), action="knowledge.upload", resource="knowledge",
        detail={"filename": file.filename, "file_size": len(content)},
    )
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
    await log_audit(
        user_id=str(current_user.id), action="knowledge.ingest", resource="knowledge",
        detail={"doc_id": doc_id, "filename": doc.filename, "status": doc.status},
    )
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
    await log_audit(
        user_id=str(current_user.id), action="knowledge.delete", resource="knowledge",
        detail={"doc_id": doc_id, "filename": doc.filename},
    )
    return ApiResponse(data=None)


@router.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: str,
    request: Request,
    token: str | None = Query(None, description="访问令牌（可选，用于浏览器直接打开）"),
    db: AsyncSession = Depends(get_db),
):
    # 支持 header 和 query param 两种传 token 方式
    auth = request.headers.get("Authorization", "")
    access_token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else token
    if not access_token:
        raise HTTPException(status_code=401, detail="未登录")

    payload = decode_token(access_token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.id == payload["sub"])
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    if user.role.name not in ("admin", "lawyer"):
        raise HTTPException(status_code=403, detail="权限不足")

    doc_result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    media_type = "application/pdf" if doc.filename.endswith(".pdf") else "application/octet-stream"
    from urllib.parse import quote
    encoded_name = quote(doc.filename)
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{encoded_name}"},
    )


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
