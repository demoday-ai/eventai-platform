"""Admin conversation endpoints (unified chat_messages view + organizer takeover)."""
import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_organizer
from app.database import get_session
from app.models.user import User
from app.schemas.support import (
    ConversationListResponse,
    ConversationMessageResponse,
    SendMessageRequest,
)
from app.services.admin import conversation_service
from app.services.core import user_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    filter: Literal["all", "attention", "taken_over"] = "all",
    role: str | None = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")
    return await conversation_service.get_conversations(db, event.id, filter=filter, role=role)


@router.get(
    "/conversations/{user_id}/messages",
    response_model=list[ConversationMessageResponse],
)
async def get_conversation_messages(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")
    return await conversation_service.get_messages(db, user_id, event.id)


@router.post(
    "/conversations/{user_id}/reply", response_model=ConversationMessageResponse
)
async def reply_to_conversation(
    user_id: UUID,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")
    msg = await conversation_service.post_organizer_message(
        db, user_id, event.id, current_user.id, body.text
    )
    await db.commit()

    target = await db.get(User, user_id)
    if target and target.telegram_user_id:
        try:
            from app.services.core.bot_messenger import get_send_bot

            bot = get_send_bot()
            org_name = current_user.full_name or "Организатор"
            await bot.send_message(
                chat_id=int(target.telegram_user_id),
                text=f"Ответ от организатора ({org_name}):\n\n{body.text}",
            )
        except Exception as e:
            logger.warning("Failed to deliver organizer message via Telegram: %s", e)
    return msg


@router.post("/conversations/{user_id}/release")
async def release_conversation(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")
    await conversation_service.release(db, user_id, event.id)
    await db.commit()
    return {"status": "released"}


@router.post("/conversations/{user_id}/close")
async def close_conversation(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")
    await conversation_service.close(db, user_id, event.id)
    await db.commit()
    return {"status": "closed"}
