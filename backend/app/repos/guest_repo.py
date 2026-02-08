"""Guest data access."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_profile import BusinessProfile
from app.models.guest_profile import GuestProfile


async def get_guest_profile(
    session: AsyncSession, user_id: UUID, event_id: UUID
) -> GuestProfile | None:
    result = await session.execute(
        select(GuestProfile).where(
            GuestProfile.user_id == user_id,
            GuestProfile.event_id == event_id,
        )
    )
    return result.scalar_one_or_none()


async def get_business_profile(
    session: AsyncSession, user_id: UUID, event_id: UUID
) -> BusinessProfile | None:
    result = await session.execute(
        select(BusinessProfile).where(
            BusinessProfile.user_id == user_id,
            BusinessProfile.event_id == event_id,
        )
    )
    return result.scalar_one_or_none()
