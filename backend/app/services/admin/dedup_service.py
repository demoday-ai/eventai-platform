"""Deduplication service for file uploads.

Uses audit_log to detect recently uploaded identical files.
"""

import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AdminAuditLog


def compute_file_hash(content: bytes) -> str:
    """Compute SHA-256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


async def check_recent_duplicate(
    session: AsyncSession,
    file_hash: str,
    action: str,
    window_minutes: int = 10,
) -> dict | None:
    """Check if the same file was uploaded recently.

    Queries AdminAuditLog for matching action + file_hash in details within window.
    Returns {warning, previous_upload_at, user_name} or None.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

    result = await session.execute(
        select(AdminAuditLog)
        .where(AdminAuditLog.action == action)
        .where(AdminAuditLog.created_at >= cutoff)
        .where(AdminAuditLog.details["file_hash"].as_string() == file_hash)
        .order_by(AdminAuditLog.created_at.desc())
        .limit(1)
    )
    prev = result.scalars().first()

    if prev:
        return {
            "warning": (
                f"Этот файл уже был загружен {prev.created_at.strftime('%H:%M:%S')}"
                f" пользователем {prev.user_name or 'неизвестно'}"
            ),
            "previous_upload_at": prev.created_at.isoformat(),
            "user_name": prev.user_name,
        }

    return None
