"""Audit log query API — list and search operation logs."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.common import ApiResponse

router = APIRouter()


@router.get("")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    action: str | None = None,
    resource: str | None = None,
    user_id: str | None = None,
    keyword: str | None = None,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog).order_by(AuditLog.created_at.desc())

    if action:
        query = query.where(AuditLog.action == action)
    if resource:
        query = query.where(AuditLog.resource.ilike(f"%{resource}%"))
    if user_id:
        from uuid import UUID
        query = query.where(AuditLog.user_id == UUID(user_id))
    if keyword:
        query = query.where(AuditLog.detail.cast(str).ilike(f"%{keyword}%"))

    # Total count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    return ApiResponse(data={
        "items": [_audit_info(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/actions")
async def list_audit_actions(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Return distinct action values for the filter dropdown."""
    result = await db.execute(
        select(AuditLog.action).distinct().order_by(AuditLog.action)
    )
    actions = [row[0] for row in result.all()]
    return ApiResponse(data=actions)


def _audit_info(r: AuditLog) -> dict:
    return {
        "id": r.id,
        "user_id": str(r.user_id) if r.user_id else None,
        "action": r.action,
        "resource": r.resource,
        "detail": r.detail,
        "ip_address": r.ip_address,
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }
