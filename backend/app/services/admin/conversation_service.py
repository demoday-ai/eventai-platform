"""Unified conversation service.

Messages live in chat_messages (single source of truth, roles
user/assistant/organizer); per-(user,event) state (needs_attention, status,
taken_over) lives in support_threads. The admin works by user_id.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage
from app.models.role import Role
from app.models.support_thread import SupportThread
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.support import (
    ConversationListResponse,
    ConversationMessageResponse,
    ConversationResponse,
)


async def get_conversations(
    session: AsyncSession,
    event_id: UUID,
    filter: str = "all",
    role: str | None = None,
) -> ConversationListResponse:
    """List conversations: every user with chat_messages in the event, plus
    support_threads metadata. filter in {all, attention, taken_over}."""
    users = (
        await session.execute(
            select(User).where(
                User.id.in_(
                    select(ChatMessage.user_id)
                    .where(ChatMessage.event_id == event_id)
                    .distinct()
                )
            )
        )
    ).scalars().all()
    if not users:
        return ConversationListResponse(conversations=[], total=0)

    uids = [u.id for u in users]

    counts = dict(
        (
            await session.execute(
                select(ChatMessage.user_id, func.count(ChatMessage.id))
                .where(ChatMessage.event_id == event_id, ChatMessage.user_id.in_(uids))
                .group_by(ChatMessage.user_id)
            )
        ).all()
    )

    # Last message per user: fetch all (event is bounded ~hundreds of guests),
    # reduce in Python so it works identically on SQLite (tests) and Postgres.
    all_msgs = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.event_id == event_id, ChatMessage.user_id.in_(uids))
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
    ).scalars().all()
    last_by_user: dict[UUID, ChatMessage] = {}
    for m in all_msgs:
        last_by_user[m.user_id] = m  # ascending order -> last write wins

    threads = (
        await session.execute(
            select(SupportThread).where(
                SupportThread.event_id == event_id, SupportThread.user_id.in_(uids)
            )
        )
    ).scalars().all()
    thread_by_user = {t.user_id: t for t in threads}

    role_by_user = dict(
        (
            await session.execute(
                select(UserRole.user_id, Role.code)
                .join(Role)
                .where(UserRole.user_id.in_(uids), UserRole.event_id == event_id)
            )
        ).all()
    )

    items: list[ConversationResponse] = []
    for u in users:
        t = thread_by_user.get(u.id)
        last = last_by_user.get(u.id)
        needs_attention = t.needs_attention if t else False
        taken_over = t.taken_over if t else False
        status = t.status if t else "open"
        user_role = role_by_user.get(u.id)

        if filter == "attention" and not needs_attention:
            continue
        if filter == "taken_over" and not taken_over:
            continue
        if role and user_role != role:
            continue

        items.append(
            ConversationResponse(
                user_id=str(u.id),
                user_name=u.full_name or u.username or "N/A",
                user_username=u.username,
                user_role=user_role,
                last_message=last.content[:100] if last else None,
                last_message_at=last.created_at.isoformat() if last else None,
                message_count=counts.get(u.id, 0),
                unread=(last.role == "user") if last else False,
                needs_attention=needs_attention,
                taken_over=taken_over,
                status=status,
            )
        )
    return ConversationListResponse(conversations=items, total=len(items))


async def get_messages(
    session: AsyncSession, user_id: UUID, event_id: UUID
) -> list[ConversationMessageResponse]:
    rows = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id, ChatMessage.event_id == event_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
    ).scalars().all()
    return [
        ConversationMessageResponse(
            id=str(m.id),
            role=m.role,
            content=m.content,
            created_at=m.created_at.isoformat(),
        )
        for m in rows
    ]


async def _get_or_create_thread(
    session: AsyncSession, user_id: UUID, event_id: UUID
) -> SupportThread:
    thread = (
        await session.execute(
            select(SupportThread)
            .where(SupportThread.user_id == user_id, SupportThread.event_id == event_id)
            .order_by(SupportThread.created_at.desc())
            .limit(1)
            .with_for_update(skip_locked=False)
        )
    ).scalar_one_or_none()
    if thread:
        return thread
    thread = SupportThread(user_id=user_id, event_id=event_id, status="open")
    session.add(thread)
    await session.flush()
    return thread


async def post_organizer_message(
    session: AsyncSession,
    user_id: UUID,
    event_id: UUID,
    organizer_id: UUID,
    text: str,
) -> ConversationMessageResponse:
    """Persist an organizer message into chat_messages and take over the chat."""
    msg = ChatMessage(user_id=user_id, event_id=event_id, role="organizer", content=text)
    session.add(msg)
    thread = await _get_or_create_thread(session, user_id, event_id)
    thread.taken_over = True
    thread.needs_attention = False
    thread.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(msg)
    return ConversationMessageResponse(
        id=str(msg.id), role=msg.role, content=msg.content,
        created_at=msg.created_at.isoformat(),
    )


async def release(session: AsyncSession, user_id: UUID, event_id: UUID) -> None:
    thread = await _get_or_create_thread(session, user_id, event_id)
    thread.taken_over = False
    thread.updated_at = datetime.now(timezone.utc)
    await session.flush()


async def close(session: AsyncSession, user_id: UUID, event_id: UUID) -> None:
    thread = await _get_or_create_thread(session, user_id, event_id)
    thread.status = "closed"
    thread.taken_over = False
    thread.updated_at = datetime.now(timezone.utc)
    await session.flush()
