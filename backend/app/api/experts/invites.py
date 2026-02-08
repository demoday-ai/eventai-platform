"""Expert invite endpoints: preview, confirm."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models.user import User
from app.services.admin import invite_service

router = APIRouter()


@router.get("/invites/preview")
async def invite_preview_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    from app.services.core import user_service
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    preview = await invite_service.get_invite_preview(session, event.id)
    if not preview:
        raise HTTPException(
            status_code=404,
            detail="Нет матчинга для предпросмотра. Сначала запустите матчинг экспертов.",
        )
    return preview


@router.post("/invites/confirm")
async def invite_confirm_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    from app.services.core import user_service
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    result = await invite_service.confirm_invites(session, event.id)
    return result
