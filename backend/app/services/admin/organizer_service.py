"""Organizer management service.

Provides DB-backed organizer checks with env variable fallback.
"""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.organizer import Organizer

logger = logging.getLogger(__name__)


async def is_organizer(
    session: AsyncSession,
    telegram_id: str,
    username: str | None = None,
) -> bool:
    """Check if user is an organizer by DB lookup, then env fallback."""
    # DB check
    result = await session.scalar(select(func.count(Organizer.id)).where(Organizer.telegram_id == telegram_id))
    if result and result > 0:
        return True

    # Env fallback
    return settings.is_organizer(telegram_id, username)


async def seed_from_env(session: AsyncSession) -> int:
    """Seed organizers from env variables if the table is empty."""
    count = await session.scalar(select(func.count(Organizer.id)))
    if count and count > 0:
        return 0

    seeded = 0
    for tid in settings.organizer_ids:
        existing = await session.scalar(select(Organizer).where(Organizer.telegram_id == tid))
        if not existing:
            organizer = Organizer(
                telegram_id=tid,
                added_by="env_seed",
            )
            session.add(organizer)
            seeded += 1

    if seeded:
        await session.commit()
        logger.info("Seeded %d organizers from env", seeded)

    return seeded


async def list_organizers(session: AsyncSession) -> list[Organizer]:
    """List all organizers."""
    result = await session.execute(select(Organizer).order_by(Organizer.created_at))
    return list(result.scalars().all())


async def add_organizer(
    session: AsyncSession,
    telegram_id: str,
    telegram_username: str | None = None,
    name: str | None = None,
    added_by: str | None = None,
) -> Organizer:
    """Add a new organizer."""
    organizer = Organizer(
        telegram_id=telegram_id,
        telegram_username=telegram_username,
        name=name,
        added_by=added_by,
    )
    session.add(organizer)
    await session.flush()
    return organizer


async def remove_organizer(session: AsyncSession, organizer_id: UUID) -> bool:
    """Remove an organizer by ID. Returns True if deleted."""
    organizer = await session.get(Organizer, organizer_id)
    if not organizer:
        return False
    await session.delete(organizer)
    await session.flush()
    return True
