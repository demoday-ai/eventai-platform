"""User service with database access logic."""

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_profile import BusinessProfile
from app.models.event import Event
from app.models.guest_profile import GuestProfile
from app.models.role import Role, RoleCode
from app.models.user import GUEST_SUBTYPE_TO_ROLE_CODE, GuestSubtype, User, UserRoleCode
from app.models.user_role import UserRole


async def upsert_user(
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
    user = result.scalars().one()
    await session.commit()
    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_user_id: str) -> User | None:
    result = await session.execute(select(User).where(User.telegram_user_id == telegram_user_id))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def get_current_event(session: AsyncSession) -> Event | None:
    """Get the most recent event by start_date."""
    result = await session.execute(select(Event).order_by(Event.start_date.desc()).limit(1))
    return result.scalar_one_or_none()


async def get_role_by_code(session: AsyncSession, code: RoleCode) -> Role | None:
    result = await session.execute(select(Role).where(Role.code == code.value))
    return result.scalar_one_or_none()


async def get_user_role(session: AsyncSession, user_id: uuid.UUID, event_id: uuid.UUID) -> UserRole | None:
    result = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.event_id == event_id,
        )
    )
    return result.scalar_one_or_none()


async def get_user_role_with_info(session: AsyncSession, user_id: uuid.UUID, event_id: uuid.UUID) -> Role | None:
    result = await session.execute(
        select(Role)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id, UserRole.event_id == event_id)
    )
    return result.scalar_one_or_none()


async def set_role(
    session: AsyncSession,
    user_id: uuid.UUID,
    event_id: uuid.UUID,
    role: Role,
    guest_subtype: GuestSubtype | None = None,
) -> None:
    # Get existing user_role
    result = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.event_id == event_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.role_id = role.id
    else:
        user_role = UserRole(user_id=user_id, role_id=role.id, event_id=event_id)
        session.add(user_role)

    # Update guest_subtype + role_code on user.
    # 031-bot-replacement: role_code is the coarse 3-value enum used by the bot agent;
    # keep it in sync with guest_subtype + role.code so the bot reads correct routing.
    user = await session.get(User, user_id)
    if role.code == RoleCode.GUEST.value:
        user.guest_subtype = guest_subtype
        if guest_subtype is not None:
            user.role_code = GUEST_SUBTYPE_TO_ROLE_CODE.get(guest_subtype)
        else:
            user.role_code = UserRoleCode.GUEST
    else:
        user.guest_subtype = None
        # Map admin role codes -> bot role codes
        # (RoleCode values: guest, expert, organizer, business)
        if role.code == "expert":
            user.role_code = UserRoleCode.EXPERT
        elif role.code == "business":
            user.role_code = UserRoleCode.BUSINESS
        else:
            # organizer / unknown -> not a bot user
            user.role_code = None

    await session.commit()


async def set_guest_subtype(session: AsyncSession, user_id: uuid.UUID, guest_subtype: GuestSubtype) -> None:
    user = await session.get(User, user_id)
    user.guest_subtype = guest_subtype
    # Keep bot-side coarse role in sync.
    user.role_code = GUEST_SUBTYPE_TO_ROLE_CODE.get(guest_subtype)
    await session.commit()


async def get_guest_profile(session: AsyncSession, user_id: uuid.UUID) -> GuestProfile | None:
    result = await session.execute(select(GuestProfile).where(GuestProfile.user_id == user_id))
    return result.scalar_one_or_none()


async def get_business_profile(session: AsyncSession, user_id: uuid.UUID) -> BusinessProfile | None:
    result = await session.execute(select(BusinessProfile).where(BusinessProfile.user_id == user_id))
    return result.scalar_one_or_none()
