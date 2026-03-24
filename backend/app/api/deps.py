import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import decode_token
from app.config import Settings
from app.database import get_session
from app.models.user import User
from app.services.core import user_service

bearer_scheme = HTTPBearer(auto_error=False)
_settings = Settings()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not credentials:
        # Dev fallback only in development
        if os.getenv("ENVIRONMENT", "development") == "development":
            return await user_service.upsert_user(
                session,
                telegram_user_id="dev-admin",
                full_name="Dev Admin",
                username="dev-admin",
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    telegram_user_id = decode_token(credentials.credentials)
    user = await user_service.get_user_by_telegram_id(session, telegram_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    return user


async def check_organizer(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency that checks if the current user is an organizer."""
    # Dev-admin bypass in development
    if current_user.telegram_user_id == "dev-admin" and os.getenv("ENVIRONMENT", "development") == "development":
        return current_user
    if _settings.is_organizer(current_user.telegram_user_id, current_user.username):
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organizer access required")


async def get_current_user_id(current_user: User = Depends(get_current_user)) -> str:
    """Get telegram_id of the current user."""
    return current_user.telegram_user_id


# Alias for get_session (used in some routes)
get_db = get_session
