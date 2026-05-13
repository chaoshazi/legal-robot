import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.consultation import Consultation
from app.models.message import Message
from app.models.user import User
from app.schemas.common import ApiResponse
from pydantic import BaseModel

router = APIRouter()


class ConsultationInfo(BaseModel):
    id: str
    user_id: str
    session_id: str
    question: str
    draft_answer: str | None
    final_answer: str | None
    status: str
    reviewer_id: str | None
    review_comment: str | None
    created_at: str
    reviewed_at: str | None


class ReviewRequest(BaseModel):
    action: str  # publish / reject
    final_answer: str | None = None
    comment: str | None = None


@router.get("")
async def list_consultations(
    status_filter: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Consultation)
    if current_user.role.name == "user":
        query = query.where(Consultation.user_id == current_user.id)
    if status_filter:
        query = query.where(Consultation.status == status_filter)
    query = query.order_by(Consultation.created_at.desc())

    result = await db.execute(query)
    consultations = result.scalars().all()
    return ApiResponse(data=[_consultation_info(c) for c in consultations])


@router.get("/pending")
async def list_pending(
    current_user: User = Depends(require_role("lawyer", "admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Consultation).where(Consultation.status == "draft").order_by(Consultation.created_at)
    )
    consultations = result.scalars().all()
    return ApiResponse(data=[_consultation_info(c) for c in consultations])


@router.post("/{consultation_id}/review")
async def review_consultation(
    consultation_id: str,
    req: ReviewRequest,
    current_user: User = Depends(require_role("lawyer", "admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Consultation).where(Consultation.id == consultation_id))
    consultation = result.scalar_one_or_none()
    if not consultation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found")
    if consultation.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already reviewed")

    if req.action == "publish":
        consultation.status = "published"
        consultation.final_answer = req.final_answer or consultation.draft_answer
        # Sync the chat message so the user sees the lawyer's edited answer
        msg_result = await db.execute(
            select(Message)
            .where(
                Message.session_id == consultation.session_id,
                Message.role == "assistant",
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        assistant_msg = msg_result.scalar_one_or_none()
        if assistant_msg:
            assistant_msg.content = consultation.final_answer
    elif req.action == "reject":
        consultation.status = "rejected"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action")

    consultation.reviewer_id = current_user.id
    consultation.review_comment = req.comment
    consultation.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(consultation)
    return ApiResponse(data=_consultation_info(consultation))


def _consultation_info(c: Consultation) -> ConsultationInfo:
    return ConsultationInfo(
        id=str(c.id),
        user_id=str(c.user_id),
        session_id=str(c.session_id),
        question=c.question,
        draft_answer=c.draft_answer,
        final_answer=c.final_answer,
        status=c.status,
        reviewer_id=str(c.reviewer_id) if c.reviewer_id else None,
        review_comment=c.review_comment,
        created_at=c.created_at.isoformat() if c.created_at else "",
        reviewed_at=c.reviewed_at.isoformat() if c.reviewed_at else None,
    )
