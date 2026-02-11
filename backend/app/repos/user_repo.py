"""User data access."""

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_profile import BusinessProfile
from app.models.guest_profile import GuestProfile
from app.models.role import Role, RoleCode
from app.models.user import User
from app.models.user_role import UserRole


async def upsert(
    session: AsyncSession,
    telegram_user_id: str,
    full_name: str,
    username: str | None = None,
    source: str | None = None,
) -> User:
    """Create or update user by telegram_user_id."""
    values: dict = {
        "id": uuid.uuid4(),
        "telegram_user_id": telegram_user_id,
        "full_name": full_name,
        "username": username,
    }
    if source is not None:
        values["source"] = source

    stmt = (
        pg_insert(User)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["telegram_user_id"],
            set_={"full_name": full_name, "username": username},
        )
        .returning(User)
    )
    result = await session.execute(stmt)
    return result.scalars().one()


async def get_by_telegram_id(
    session: AsyncSession, telegram_user_id: str
) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def get_role_by_code(session: AsyncSession, code: RoleCode) -> Role | None:
    result = await session.execute(select(Role).where(Role.code == code.value))
    return result.scalar_one_or_none()


async def get_user_role(
    session: AsyncSession, user_id: uuid.UUID, event_id: uuid.UUID
) -> UserRole | None:
    result = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.event_id == event_id,
        )
    )
    return result.scalar_one_or_none()


async def get_user_role_with_info(
    session: AsyncSession, user_id: uuid.UUID, event_id: uuid.UUID
) -> Role | None:
    result = await session.execute(
        select(Role)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id, UserRole.event_id == event_id)
    )
    return result.scalar_one_or_none()


async def get_guest_profile(
    session: AsyncSession, user_id: uuid.UUID
) -> GuestProfile | None:
    result = await session.execute(
        select(GuestProfile).where(GuestProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_business_profile(
    session: AsyncSession, user_id: uuid.UUID
) -> BusinessProfile | None:
    result = await session.execute(
        select(BusinessProfile).where(BusinessProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()
