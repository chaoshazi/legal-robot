"""Audit logging service.

Usage:
    await log_audit(
        user_id=current_user.id,
        action="login",
        resource="auth",
        detail={"email": "admin@example.com"},
        ip_address=request.client.host,
    )
"""

from app.core.database import async_session
from app.models.audit import AuditLog


async def log_audit(
    user_id: str | None,
    action: str,
    resource: str,
    detail: dict | None = None,
    ip_address: str | None = None,
):
    """Write an audit log entry using its own DB session."""
    async with async_session() as db:
        db.add(AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            detail=detail or {},
            ip_address=ip_address,
        ))
        await db.commit()
