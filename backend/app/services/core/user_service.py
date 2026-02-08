"""User service — thin wrapper over user_repo and event_repo."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_profile import BusinessProfile
from app.models.event import Event
from app.models.guest_profile import GuestProfile
from app.models.role import Role, RoleCode
from app.models.user import GuestSubtype, User
from app.models.user_role import UserRole
from app.repos import event_repo, user_repo


async def upsert_user(
    session: AsyncSession,
    telegram_user_id: str,
    full_name: str,
    username: str | None = None,
) -> User:
    user = await user_repo.upsert(session, telegram_user_id, full_name, username)
    await session.commit()
    return user


async def get_user_by_telegram_id(
    session: AsyncSession, telegram_user_id: str
) -> User | None:
    return await user_repo.get_by_telegram_id(session, telegram_user_id)


async def get_user_by_id(
    session: AsyncSession, user_id: uuid.UUID
) -> User | None:
    return await user_repo.get_by_id(session, user_id)


async def get_current_event(session: AsyncSession) -> Event | None:
    return await event_repo.get_current_event(session)


async def get_role_by_code(session: AsyncSession, code: RoleCode) -> Role | None:
    return await user_repo.get_role_by_code(session, code)


async def get_user_role(
    session: AsyncSession, user_id: uuid.UUID, event_id: uuid.UUID
) -> UserRole | None:
    return await user_repo.get_user_role(session, user_id, event_id)


async def get_user_role_with_info(
    session: AsyncSession, user_id: uuid.UUID, event_id: uuid.UUID
) -> Role | None:
    return await user_repo.get_user_role_with_info(session, user_id, event_id)


async def set_role(
    session: AsyncSession,
    user_id: uuid.UUID,
    event_id: uuid.UUID,
    role: Role,
    guest_subtype: GuestSubtype | None = None,
) -> None:
    existing = await user_repo.get_user_role(session, user_id, event_id)

    if existing:
        existing.role_id = role.id
    else:
        user_role = UserRole(user_id=user_id, role_id=role.id, event_id=event_id)
        session.add(user_role)

    # Update guest_subtype on user
    user = await session.get(User, user_id)
    if role.code == RoleCode.GUEST.value:
        user.guest_subtype = guest_subtype
    else:
        user.guest_subtype = None

    await session.commit()


async def set_guest_subtype(
    session: AsyncSession, user_id: uuid.UUID, guest_subtype: GuestSubtype
) -> None:
    user = await session.get(User, user_id)
    user.guest_subtype = guest_subtype
    await session.commit()


async def get_guest_profile(
    session: AsyncSession, user_id: uuid.UUID
) -> GuestProfile | None:
    return await user_repo.get_guest_profile(session, user_id)


async def get_business_profile(
    session: AsyncSession, user_id: uuid.UUID
) -> BusinessProfile | None:
    return await user_repo.get_business_profile(session, user_id)
