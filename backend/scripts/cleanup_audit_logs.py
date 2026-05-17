"""Delete audit log entries older than 180 days.

Usage:
    python scripts/cleanup_audit_logs.py          # dry-run
    python scripts/cleanup_audit_logs.py --force   # actually delete
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")

from app.core.database import async_session
from app.models.audit import AuditLog
from sqlalchemy import delete, select, func


RETENTION_DAYS = 180


async def cleanup(dry_run: bool = True) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)

    async with async_session() as db:
        if dry_run:
            result = await db.execute(
                select(func.count()).select_from(AuditLog).where(AuditLog.created_at < cutoff)
            )
            count = result.scalar()
        else:
            result = await db.execute(
                delete(AuditLog).where(AuditLog.created_at < cutoff).returning(AuditLog.id)
            )
            rows = result.fetchall()
            count = len(rows)
            await db.commit()

    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up old audit logs")
    parser.add_argument("--force", action="store_true", help="Actually delete (default: dry-run)")
    args = parser.parse_args()

    count = asyncio.run(cleanup(dry_run=not args.force))
    action = "would be deleted" if not args.force else "deleted"
    print(f"Audit log entries older than {RETENTION_DAYS} days: {count} {action}")
