"""Admin support chat endpoints."""

import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_organizer
from app.database import get_session
from app.models.support_thread import SupportThread
from app.models.user import User
from app.schemas.support import (
    CreateThreadRequest,
    MessageResponse,
    SendMessageRequest,
    ThreadListResponse,
    UnreadCountResponse,
)
from app.services.admin import support_service
from app.services.core import user_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/support/threads", response_model=ThreadListResponse)
async def list_threads(
    status: Literal["open", "closed"] | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    """List support threads."""
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")
    return await support_service.get_threads(db, event.id, status, limit, offset)


@router.get("/support/threads/{thread_id}/messages", response_model=list[MessageResponse])
async def get_thread_messages(
    thread_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    """Get messages in a thread."""
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")
    try:
        return await support_service.get_messages(db, thread_id, event.id, limit, offset)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/support/threads/{thread_id}/reply", response_model=MessageResponse)
async def reply_to_thread(
    thread_id: UUID,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    """Send organizer reply and deliver to user via Telegram."""
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")
    try:
        msg = await support_service.send_organizer_reply(
            db, thread_id, event.id, current_user.id, body.text
        )
        await db.commit()

        # Deliver message to user via Telegram bot
        thread = await db.get(SupportThread, thread_id)
        if thread:
            user = await db.get(User, thread.user_id)
            if user and user.telegram_user_id:
                try:
                    from app.services.core.bot_messenger import get_send_bot

                    bot = get_send_bot()
                    org_name = current_user.full_name or "Организатор"
                    # The bot/ service shows guests how to keep talking via /support;
                    # no inline keyboard from backend needed for plain text reply.
                    await bot.send_message(
                        chat_id=int(user.telegram_user_id),
                        text=f"Ответ от организатора ({org_name}):\n\n{body.text}",
                    )
                except Exception as e:
                    logger.warning("Failed to deliver support reply via Telegram: %s", e)

        return MessageResponse(
            id=str(msg.id),
            sender_type="organizer",
            sender_name=current_user.full_name or current_user.username or "Организатор",
            text=msg.text,
            created_at=msg.created_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/support/threads/{thread_id}/close")
async def close_thread(
    thread_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    """Close a support thread."""
    try:
        thread = await support_service.close_thread(db, thread_id, closed_by="organizer")
        return {"status": "closed", "thread_id": str(thread.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/support/threads", response_model=dict)
async def create_thread(
    body: CreateThreadRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    """Organizer creates thread to contact a specific user."""
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    thread = await support_service.create_thread_for_user(
        db, event.id, UUID(body.user_id), current_user.id, body.message
    )
    return {"thread_id": str(thread.id), "status": thread.status}


@router.post("/support/threads/{thread_id}/dismiss-attention")
async def dismiss_attention(
    thread_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    """Organizer dismisses the 'needs attention' flag."""
    thread = await db.get(SupportThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    thread.needs_attention = False
    await db.commit()
    return {"status": "ok"}


@router.get("/support/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    """Get count of threads with unread user messages."""
    event = await user_service.get_current_event(db)
    if not event:
        return UnreadCountResponse(count=0)
    count = await support_service.get_unread_count(db, event.id)
    return UnreadCountResponse(count=count)
