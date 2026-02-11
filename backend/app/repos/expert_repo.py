"""Expert data access."""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.expert import Expert
from app.models.expert_room_assignment import ExpertRoomAssignment
from app.models.expert_tag import ExpertTag
from app.models.tag import Tag


async def get_by_id(session: AsyncSession, expert_id: UUID) -> Expert | None:
    return await session.get(Expert, expert_id)


async def get_detail(session: AsyncSession, expert_id: UUID) -> Expert | None:
    """Get expert with tags and assignments eagerly loaded."""
    result = await session.execute(
        select(Expert)
        .where(Expert.id == expert_id)
        .options(
            selectinload(Expert.tags).selectinload(ExpertTag.tag),
            selectinload(Expert.assignments).selectinload(ExpertRoomAssignment.room),
        )
    )
    return result.scalars().first()


async def get_by_telegram(session: AsyncSession, username: str) -> Expert | None:
    """Get expert by telegram username."""
    result = await session.execute(select(Expert).where(Expert.telegram_username == username))
    return result.scalar_one_or_none()


async def get_experts(
    session: AsyncSession,
    event_id: UUID,
    has_tags: bool | None = None,
    tag_name: str | None = None,
    search: str | None = None,
) -> list[Expert]:
    """List experts with optional filters."""
    query = (
        select(Expert)
        .where(Expert.event_id == event_id)
        .options(
            selectinload(Expert.tags).selectinload(ExpertTag.tag),
            selectinload(Expert.assignments),
        )
    )

    if has_tags is True:
        query = query.where(Expert.id.in_(select(ExpertTag.expert_id).distinct()))
    elif has_tags is False:
        query = query.where(~Expert.id.in_(select(ExpertTag.expert_id).distinct()))

    if tag_name:
        query = query.where(
            Expert.id.in_(select(ExpertTag.expert_id).join(Tag, ExpertTag.tag_id == Tag.id).where(Tag.name == tag_name))
        )

    if search:
        pattern = f"%{search}%"
        query = query.where(Expert.name.ilike(pattern) | Expert.telegram_username.ilike(pattern))

    result = await session.execute(query.order_by(Expert.name))
    return list(result.scalars().all())


async def count_by_event(session: AsyncSession, event_id: UUID) -> int:
    return await session.scalar(select(func.count(Expert.id)).where(Expert.event_id == event_id)) or 0


async def delete_all_by_event(session: AsyncSession, event_id: UUID) -> None:
    """Delete all experts for an event (cascade handles tags/assignments)."""
    experts = await session.execute(select(Expert.id).where(Expert.event_id == event_id))
    expert_ids = [row[0] for row in experts.all()]
    if expert_ids:
        await session.execute(delete(ExpertTag).where(ExpertTag.expert_id.in_(expert_ids)))
        await session.execute(delete(ExpertRoomAssignment).where(ExpertRoomAssignment.expert_id.in_(expert_ids)))
        await session.execute(delete(Expert).where(Expert.event_id == event_id))
