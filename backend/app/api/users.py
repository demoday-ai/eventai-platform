from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_session
from app.models.role import RoleCode
from app.models.user import User
from app.schemas.user import (
    RoleInfo,
    SetGuestSubtypeRequest,
    SetRoleRequest,
    UserProfile,
)
from app.services.core import user_service

router = APIRouter(prefix="/users", tags=["Users"])


def _build_profile(user: User, role_info: RoleInfo | None) -> UserProfile:
    return UserProfile(
        id=user.id,
        telegram_user_id=user.telegram_user_id,
        full_name=user.full_name,
        username=user.username,
        role=role_info,
        guest_subtype=user.guest_subtype,
    )


@router.put("/me/role", response_model=UserProfile)
async def set_my_role(
    body: SetRoleRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if body.role_code == RoleCode.ORGANIZER:
        if user.telegram_user_id not in settings.organizer_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Роль организатора доступна только по приглашению",
            )

    role = await user_service.get_role_by_code(session, body.role_code)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неизвестная роль")

    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Нет активного события")

    await user_service.set_role(
        session, user.id, event.id, role, guest_subtype=body.guest_subtype
    )

    await session.refresh(user)
    return _build_profile(user, RoleInfo(code=role.code, name=role.name))


@router.put("/me/guest-subtype", response_model=UserProfile)
async def set_guest_subtype(
    body: SetGuestSubtypeRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Нет активного события")

    role = await user_service.get_user_role_with_info(session, user.id, event.id)
    if not role or role.code != RoleCode.GUEST.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Установка подтипа доступна только гостям",
        )

    await user_service.set_guest_subtype(session, user.id, body.guest_subtype)
    await session.refresh(user)
    return _build_profile(user, RoleInfo(code=role.code, name=role.name))
