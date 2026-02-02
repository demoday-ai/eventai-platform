import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.role import Role, RoleCode
from app.models.user import GuestSubtype, User
from app.models.user_role import UserRole


async def upsert_user(
    session: AsyncSession,
    telegram_user_id: str,
    full_name: str,
    username: str | None = None,
) -> User:
    stmt = (
        pg_insert(User)
        .values(
            id=uuid.uuid4(),
            telegram_user_id=telegram_user_id,
            full_name=full_name,
            username=username,
        )
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


async def get_user_by_telegram_id(
    session: AsyncSession, telegram_user_id: str
) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    return result.scalar_one_or_none()


async def get_current_event(session: AsyncSession) -> Event | None:
    result = await session.execute(select(Event).order_by(Event.start_date.desc()).limit(1))
    return result.scalar_one_or_none()


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


async def set_role(
    session: AsyncSession,
    user_id: uuid.UUID,
    event_id: uuid.UUID,
    role: Role,
    guest_subtype: GuestSubtype | None = None,
) -> None:
    existing = await get_user_role(session, user_id, event_id)

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
