"""Schedule data access."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule_slot import ScheduleSlot


async def get_slot_by_id(session: AsyncSession, slot_id: UUID) -> ScheduleSlot | None:
    return await session.get(ScheduleSlot, slot_id)


async def count_empty_slots(session: AsyncSession, event_id: UUID) -> int:
    return (
        await session.scalar(
            select(func.count(ScheduleSlot.id)).where(
                ScheduleSlot.event_id == event_id,
                ScheduleSlot.project_id.is_(None),
            )
        )
        or 0
    )


async def get_slots_by_event(session: AsyncSession, event_id: UUID) -> list[ScheduleSlot]:
    result = await session.execute(
        select(ScheduleSlot).where(ScheduleSlot.event_id == event_id).order_by(ScheduleSlot.start_time)
    )
    return list(result.scalars().all())
