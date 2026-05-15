"""Upload API — file upload, ASR transcription, and download for chat attachments."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.attachment import Attachment
from app.models.user import User
from app.schemas.chat import UploadAttachmentResponse
from app.schemas.common import ApiResponse
from app.utils.file_processing import (
    detect_file_type,
    extract_text_from_file,
    extract_text_from_image,
)

router = APIRouter()
settings = get_settings()


def _get_allowed_types() -> set[str]:
    return {t.strip() for t in settings.upload_allowed_types.split(",") if t.strip()}


def _get_upload_dir() -> Path:
    path = Path(settings.upload_storage_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _validate_file(filename: str, content_type: str, file_size: int):
    """Validate file type and size."""
    max_bytes = settings.upload_max_size_mb * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制 ({settings.upload_max_size_mb}MB)",
        )

    allowed = _get_allowed_types()
    if content_type not in allowed and content_type != "application/octet-stream":
        # Check by extension as fallback
        ext = Path(filename).suffix.lower()
        type_map = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
            ".webp": "image/webp", ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".txt": "text/plain",
            ".wav": "audio/wav", ".mp3": "audio/mpeg", ".webm": "audio/webm",
        }
        mapped = type_map.get(ext, "")
        if mapped not in allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的文件类型")


@router.post("/upload")
async def upload_attachment(
    file: UploadFile = File(...),
    session_id: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file (image, audio, document) for use in chat.

    Returns an attachment ID that can be passed to /chat/stream or /chat/ask.
    For documents and images, text is extracted immediately (status=ready).
    For audio, the file is stored (status=uploaded); call /chat/transcribe to transcribe.
    """
    # Read file content
    content = await file.read()
    file_size = len(content)

    _validate_file(file.filename or "unknown", file.content_type or "", file_size)

    # Determine file type category
    file_type = detect_file_type(file.content_type or "", file.filename or "")

    # Save file to disk
    user_dir = _get_upload_dir() / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "unknown").suffix.lower()
    stored_name = f"{uuid.uuid4()}{ext}"
    file_path = user_dir / stored_name
    file_path.write_bytes(content)

    # Create attachment record
    attachment = Attachment(
        id=uuid.uuid4(),
        user_id=current_user.id,
        session_id=uuid.UUID(session_id) if session_id else None,
        file_type=file_type,
        mime_type=file.content_type or "application/octet-stream",
        filename=file.filename or "unknown",
        file_size=file_size,
        file_path=str(file_path),
        status="uploaded",
    )

    # Process file content based on type
    try:
        if file_type == "document":
            attachment.status = "processing"
            text = extract_text_from_file(str(file_path))
            if text:
                # Truncate to prevent context overflow
                max_chars = 8000
                if len(text) > max_chars:
                    text = text[:max_chars] + f"\n\n...（文件内容过长，仅展示前{max_chars}字符）"
                attachment.extracted_text = text
            attachment.status = "ready"

        elif file_type == "image":
            attachment.status = "processing"
            text = extract_text_from_image(str(file_path))
            if text:
                attachment.extracted_text = text
            attachment.status = "ready"

        # Audio stays as "uploaded" — transcribed separately
    except Exception as e:
        attachment.status = "failed"
        attachment.error = str(e)

    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    # Compute static URL for file serving
    static_url = ""
    try:
        rel_path = str(Path(attachment.file_path).relative_to(_get_upload_dir().parent))
        static_url = f"/{rel_path}"
    except ValueError:
        pass

    return ApiResponse(data=UploadAttachmentResponse(
        id=str(attachment.id),
        filename=attachment.filename,
        file_size=attachment.file_size,
        file_type=attachment.file_type,
        mime_type=attachment.mime_type,
        status=attachment.status,
        url=static_url,
    ))


@router.post("/transcribe/{attachment_id}")
async def transcribe_audio(
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Transcribe an audio attachment using faster-whisper."""
    result = await db.execute(
        select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.user_id == current_user.id,
        )
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="附件不存在")

    if attachment.file_type != "audio":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持音频文件转写")

    if attachment.status == "ready" and attachment.transcription:
        return ApiResponse(data={"transcription": attachment.transcription, "attachment_id": attachment_id})

    # Run faster-whisper
    attachment.status = "processing"
    await db.commit()

    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(
            settings.asr_model_size,
            device="cpu",
            compute_type="int8",
            download_root=None,
        )
        segments, info = model.transcribe(str(attachment.file_path), language="zh")

        text = " ".join(seg.text for seg in segments)

        attachment.transcription = text
        attachment.status = "ready"
        await db.commit()

        return ApiResponse(data={"transcription": text, "attachment_id": attachment_id})

    except Exception as e:
        attachment.status = "failed"
        attachment.error = str(e)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"转写失败: {e}")


@router.get("/download/{attachment_id}")
async def download_attachment(
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download an attachment file with authentication."""
    result = await db.execute(
        select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.user_id == current_user.id,
        )
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="附件不存在")

    file_path = Path(attachment.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    return FileResponse(
        path=str(file_path),
        filename=attachment.filename,
        media_type=attachment.mime_type,
    )
