import hashlib
import hmac
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


def _verify_telegram_login(body: TelegramAuthRequest) -> None:
    if not settings.bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram bot token не настроен",
        )

    if not body.hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не предоставлена подпись Telegram",
        )

    payload_fields = {
        "auth_date": str(body.auth_date),
        "id": body.telegram_user_id,
    }
    for key in ("first_name", "last_name", "username", "photo_url"):
        value = getattr(body, key)
        if value:
            payload_fields[key] = value

    data_check_string = "\n".join(
        f"{key}={payload_fields[key]}" for key in sorted(payload_fields)
    )
    secret = hashlib.sha256(settings.bot_token.encode()).digest()
    signature = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, body.hash.lower()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверная подпись Telegram",
        )

    now_ts = datetime.now(timezone.utc).timestamp()
    if abs(now_ts - body.auth_date) > timedelta(minutes=5).total_seconds():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Истёк срок действия данных Telegram",
        )


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


@router.post("/dev-login", response_model=AuthResponse)
async def dev_login(telegram_id: str, session: AsyncSession = Depends(get_session)):
    """Dev-only login endpoint. Accepts telegram_id without verification.

    Automatically assigns organizer role for admin panel access.
    """
    from app.models.role import RoleCode

    user = await user_service.upsert_user(
        session,
        telegram_user_id=telegram_id,
        full_name=f"Dev User {telegram_id}",
        username=None,
    )

    event = await user_service.get_current_event(session)
    role_info = None
    if event:
        # Auto-assign organizer role for dev login
        organizer_role = await user_service.get_role_by_code(session, RoleCode.ORGANIZER)
        if organizer_role:
            await user_service.set_role(session, user.id, event.id, organizer_role)
            await session.commit()
            role_info = RoleInfo(code=organizer_role.code, name=organizer_role.name)

    token = create_access_token(telegram_id)

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


@router.post("/login", response_model=AuthResponse)
async def login(body: TelegramAuthRequest, session: AsyncSession = Depends(get_session)):
    _verify_telegram_login(body)

    full_name = (body.full_name or " ").strip()
    if not full_name:
        first = body.first_name or ""
        last = body.last_name or ""
        full_name = f"{first} {last}".strip() or body.username or body.telegram_user_id

    user = await user_service.upsert_user(
        session,
        telegram_user_id=body.telegram_user_id,
        full_name=full_name,
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
