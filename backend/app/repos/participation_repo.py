"""Participation data access."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.participation import ParticipationRequest, ParticipationStatus


async def count_by_status(
    session: AsyncSession, event_id: UUID, statuses: list[ParticipationStatus]
) -> int:
    return await session.scalar(
        select(func.count(ParticipationRequest.id)).where(
            ParticipationRequest.event_id == event_id,
            ParticipationRequest.status.in_(statuses),
        )
    ) or 0


async def get_by_event(
    session: AsyncSession, event_id: UUID
) -> list[ParticipationRequest]:
    result = await session.execute(
        select(ParticipationRequest).where(
            ParticipationRequest.event_id == event_id
        )
    )
    return list(result.scalars().all())
