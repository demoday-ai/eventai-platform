from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.schemas.user import (
    AuthResponse,
    RoleInfo,
    TelegramAuthRequest,
    UserProfile,
)
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["Auth"])

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


def create_access_token(telegram_user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": telegram_user_id, "exp": expire},
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload["sub"]
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@router.post("/login", response_model=AuthResponse)
async def login(body: TelegramAuthRequest, session: AsyncSession = Depends(get_session)):
    user = await user_service.upsert_user(
        session,
        telegram_user_id=body.telegram_user_id,
        full_name=body.full_name,
        username=body.username,
    )

    event = await user_service.get_current_event(session)
    role_info = None
    if event:
        role = await user_service.get_user_role_with_info(session, user.id, event.id)
        if role:
            role_info = RoleInfo(code=role.code, name=role.name)

    token = create_access_token(body.telegram_user_id)

    return AuthResponse(
        access_token=token,
        user=UserProfile(
            id=user.id,
            telegram_user_id=user.telegram_user_id,
            full_name=user.full_name,
            username=user.username,
            role=role_info,
            guest_subtype=user.guest_subtype,
        ),
    )
