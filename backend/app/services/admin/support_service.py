"""Support chat service: thread management, messages, unread counts."""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Role
from app.models.support_message import SupportMessage
from app.models.support_thread import SupportThread
from app.models.user_role import UserRole
from app.schemas.support import (
    MessageResponse,
    ThreadListResponse,
    ThreadResponse,
)

logger = logging.getLogger(__name__)


async def get_threads(
    session: AsyncSession,
    event_id: UUID,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ThreadListResponse:
    """List support threads for an event."""
    query = (
        select(SupportThread)
        .where(SupportThread.event_id == event_id)
        .options(selectinload(SupportThread.user))
        .order_by(SupportThread.updated_at.desc())
    )
    if status:
        query = query.where(SupportThread.status == status)

    count_query = select(func.count(SupportThread.id)).where(SupportThread.event_id == event_id)
    if status:
        count_query = count_query.where(SupportThread.status == status)

    total = (await session.execute(count_query)).scalar() or 0
    result = await session.execute(query.limit(limit).offset(offset))
    threads = result.scalars().all()

    items = []
    for t in threads:
        # Get last message
        last_msg_result = await session.execute(
            select(SupportMessage)
            .where(SupportMessage.thread_id == t.id)
            .order_by(SupportMessage.created_at.desc())
            .limit(1)
        )
        last_msg = last_msg_result.scalar_one_or_none()

        # Count messages
        msg_count = (
            await session.execute(
                select(func.count(SupportMessage.id)).where(SupportMessage.thread_id == t.id)
            )
        ).scalar() or 0

        # Check if last message is from user (unread for organizer)
        unread = last_msg.sender_type == "user" if last_msg else False

        # Get user role
        user_role = await _get_user_primary_role(session, t.user_id, event_id)

        items.append(
            ThreadResponse(
                id=str(t.id),
                user_id=str(t.user_id),
                user_name=t.user.full_name or t.user.username or "N/A",
                user_username=t.user.username,
                user_role=user_role,
                status=t.status,
                last_message=last_msg.text[:100] if last_msg else None,
                last_message_at=last_msg.created_at.isoformat() if last_msg else None,
                unread=unread,
                message_count=msg_count,
            )
        )

    return ThreadListResponse(threads=items, total=total)


async def get_messages(
    session: AsyncSession,
    thread_id: UUID,
    limit: int = 100,
    offset: int = 0,
) -> list[MessageResponse]:
    """Get messages in a thread."""
    result = await session.execute(
        select(SupportMessage)
        .where(SupportMessage.thread_id == thread_id)
        .options(selectinload(SupportMessage.sender))
        .order_by(SupportMessage.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    messages = result.scalars().all()

    return [
        MessageResponse(
            id=str(m.id),
            sender_type=m.sender_type,
            sender_name=m.sender.full_name or m.sender.username or "N/A",
            text=m.text,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


async def send_organizer_reply(
    session: AsyncSession,
    thread_id: UUID,
    organizer_id: UUID,
    text: str,
) -> SupportMessage:
    """Send organizer reply to a thread."""
    thread = await session.get(SupportThread, thread_id)
    if not thread or thread.status != "open":
        raise ValueError("Thread not found or closed")

    msg = SupportMessage(
        thread_id=thread_id,
        sender_type="organizer",
        sender_id=organizer_id,
        text=text,
    )
    session.add(msg)
    await session.flush()
    await session.refresh(msg)
    return msg


async def create_thread_for_user(
    session: AsyncSession,
    event_id: UUID,
    user_id: UUID,
    organizer_id: UUID,
    initial_message: str,
) -> SupportThread:
    """Organizer creates a thread to contact a specific user."""
    # Check for existing open thread
    existing = await session.execute(
        select(SupportThread)
        .where(SupportThread.user_id == user_id)
        .where(SupportThread.event_id == event_id)
        .where(SupportThread.status == "open")
    )
    thread = existing.scalar_one_or_none()

    if not thread:
        thread = SupportThread(user_id=user_id, event_id=event_id, status="open")
        session.add(thread)
        await session.flush()
        await session.refresh(thread)

    msg = SupportMessage(
        thread_id=thread.id,
        sender_type="organizer",
        sender_id=organizer_id,
        text=initial_message,
    )
    session.add(msg)
    await session.commit()
    return thread


async def close_thread(
    session: AsyncSession,
    thread_id: UUID,
    closed_by: str,
) -> SupportThread:
    """Close a thread. closed_by = 'user' or 'organizer'."""
    thread = await session.get(SupportThread, thread_id)
    if not thread:
        raise ValueError("Thread not found")
    thread.status = "closed"
    thread.closed_by = closed_by
    await session.commit()
    return thread


async def get_or_create_thread(
    session: AsyncSession,
    user_id: UUID,
    event_id: UUID,
) -> SupportThread:
    """Get open thread for user or create new one."""
    result = await session.execute(
        select(SupportThread)
        .where(SupportThread.user_id == user_id)
        .where(SupportThread.event_id == event_id)
        .where(SupportThread.status == "open")
    )
    thread = result.scalar_one_or_none()
    if thread:
        return thread

    thread = SupportThread(user_id=user_id, event_id=event_id, status="open")
    session.add(thread)
    await session.flush()
    await session.refresh(thread)
    return thread


async def add_user_message(
    session: AsyncSession,
    thread_id: UUID,
    user_id: UUID,
    text: str,
) -> SupportMessage:
    """Add user message to thread."""
    msg = SupportMessage(
        thread_id=thread_id,
        sender_type="user",
        sender_id=user_id,
        text=text,
    )
    session.add(msg)
    await session.flush()
    await session.refresh(msg)
    return msg


async def get_unread_count(session: AsyncSession, event_id: UUID) -> int:
    """Count threads with last message from user (unread by organizer)."""
    count = 0
    threads_result = await session.execute(
        select(SupportThread)
        .where(SupportThread.event_id == event_id)
        .where(SupportThread.status == "open")
    )
    for thread in threads_result.scalars().all():
        last_msg = await session.execute(
            select(SupportMessage.sender_type)
            .where(SupportMessage.thread_id == thread.id)
            .order_by(SupportMessage.created_at.desc())
            .limit(1)
        )
        sender_type = last_msg.scalar_one_or_none()
        if sender_type == "user":
            count += 1
    return count


async def get_thread_messages_for_context(
    session: AsyncSession,
    thread_id: UUID,
) -> str:
    """Get full thread messages as text for AI agent context injection."""
    messages = await get_messages(session, thread_id, limit=200)
    lines = []
    for m in messages:
        role_label = "Пользователь" if m.sender_type == "user" else "Организатор"
        lines.append(f"[{role_label}] {m.sender_name}: {m.text}")
    return "\n".join(lines)


async def _get_user_primary_role(session: AsyncSession, user_id: UUID, event_id: UUID) -> str | None:
    """Get primary role for a user in an event."""
    result = await session.execute(
        select(Role.code)
        .join(UserRole)
        .where(UserRole.user_id == user_id)
        .where(UserRole.event_id == event_id)
        .limit(1)
    )
    return result.scalar_one_or_none()
