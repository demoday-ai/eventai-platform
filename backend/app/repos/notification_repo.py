"""Notification data access."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def get_by_id(session: AsyncSession, notification_id: UUID) -> Notification | None:
    return await session.get(Notification, notification_id)


async def get_pending(session: AsyncSession, limit: int = 100) -> list[Notification]:
    """Get pending notifications for delivery."""
    result = await session.execute(
        select(Notification).where(Notification.status == "PENDING").order_by(Notification.created_at).limit(limit)
    )
    return list(result.scalars().all())


async def count_by_status(session: AsyncSession, event_id: UUID, status: str) -> int:
    return (
        await session.scalar(
            select(func.count(Notification.id)).where(
                Notification.event_id == event_id,
                Notification.status == status,
            )
        )
        or 0
    )
