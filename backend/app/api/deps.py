from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import decode_token
from app.database import get_session
from app.models.user import User
from app.services import organizer_service, user_service

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    telegram_user_id = decode_token(credentials.credentials)
    user = await user_service.get_user_by_telegram_id(session, telegram_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден"
        )
    return user


async def check_organizer(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency that checks if the current user is an organizer."""
    if not current_user.telegram_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not an organizer"
        )
    if not await organizer_service.is_organizer(
        session, current_user.telegram_user_id, current_user.username,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not an organizer"
        )
    return current_user
