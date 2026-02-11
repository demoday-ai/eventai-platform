"""Admin briefing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_session
from app.models import User
from app.schemas.admin import BriefingPreview, BriefingSendResult
from app.services.admin import audit_service, briefing_service
from app.services.core import user_service

router = APIRouter()


@router.get("/briefing/preview", response_model=BriefingPreview)
async def get_briefing_preview(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get briefing preview: how many experts will receive briefings."""

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active event")

    result = await briefing_service.get_briefing_preview(db, event.id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])

    return BriefingPreview(**result)


@router.post("/briefing/send", response_model=BriefingSendResult)
async def send_briefings(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Send briefings to all confirmed experts."""

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active event")

    from telegram import Bot

    bot = Bot(token=settings.bot_token)
    result = await briefing_service.send_all_briefings(db, event.id, bot)

    await audit_service.log_action(
        db,
        current_user,
        "send_briefing",
        entity_type="briefing",
        details={"sent": result["sent"], "failed": result["failed"], "skipped": result["skipped"]},
    )
    await db.commit()

    return BriefingSendResult(**result)
