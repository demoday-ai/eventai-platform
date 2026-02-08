"""Audit logging service for admin actions."""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AdminAuditLog
from app.models.user import User

logger = logging.getLogger(__name__)


async def log_action(
    session: AsyncSession,
    user: User | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict | None = None,
) -> AdminAuditLog:
    """Create an audit log entry."""
    entry = AdminAuditLog(
        user_id=user.id if user else None,
        user_name=user.full_name if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    session.add(entry)
    await session.flush()
    return entry


async def get_audit_log(
    session: AsyncSession,
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AdminAuditLog], int]:
    """Get paginated audit log entries with optional action filter.

    Returns (entries, total_count).
    """
    base = select(AdminAuditLog)
    count_base = select(func.count(AdminAuditLog.id))

    if action:
        base = base.where(AdminAuditLog.action == action)
        count_base = count_base.where(AdminAuditLog.action == action)

    total = await session.scalar(count_base) or 0

    result = await session.execute(
        base.order_by(AdminAuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    entries = list(result.scalars().all())

    return entries, total
