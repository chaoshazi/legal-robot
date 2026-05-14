"""Evaluation query API — list and filter human evaluations."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.consultation import Consultation
from app.models.evaluation import Evaluation
from app.models.user import User
from app.schemas.common import ApiResponse

router = APIRouter()


@router.get("")
async def list_evaluations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    consultation_id: str | None = None,
    score_name: str | None = None,
    evaluated_by: str | None = None,
    current_user: User = Depends(require_role("lawyer", "admin")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Evaluation, Consultation.question)
        .join(Consultation, Evaluation.consultation_id == Consultation.id)
        .order_by(Evaluation.created_at.desc())
    )

    if consultation_id:
        from uuid import UUID
        query = query.where(Evaluation.consultation_id == UUID(consultation_id))
    if score_name:
        query = query.where(Evaluation.score_name == score_name)
    if evaluated_by:
        from uuid import UUID
        query = query.where(Evaluation.evaluated_by == UUID(evaluated_by))

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    rows = (await db.execute(query)).all()

    return ApiResponse(data={
        "items": [_evaluation_info(r, question) for r, question in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/score-names")
async def list_score_names(
    current_user: User = Depends(require_role("lawyer", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Return distinct score_name values for filter dropdown."""
    result = await db.execute(
        select(Evaluation.score_name).distinct().order_by(Evaluation.score_name)
    )
    names = [row[0] for row in result.all()]
    return ApiResponse(data=names)


def _evaluation_info(r: Evaluation, question: str = "") -> dict:
    return {
        "id": r.id,
        "consultation_id": str(r.consultation_id),
        "trace_id": r.trace_id,
        "score_name": r.score_name,
        "score_value": r.score_value,
        "data_type": r.data_type,
        "comment": r.comment,
        "evaluated_by": str(r.evaluated_by) if r.evaluated_by else None,
        "question": question[:200] if question else "",
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }
