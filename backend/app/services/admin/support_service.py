"""Support chat service: thread management, messages, unread counts."""

import logging
from datetime import datetime, timezone
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
    """List support threads for an event. Optimized: batch queries instead of N+1."""
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
    threads = list(result.scalars().all())

    if not threads:
        return ThreadListResponse(threads=[], total=total)

    thread_ids = [t.id for t in threads]
    user_ids = [t.user_id for t in threads]

    # Batch: message counts per thread
    count_result = await session.execute(
        select(SupportMessage.thread_id, func.count(SupportMessage.id))
        .where(SupportMessage.thread_id.in_(thread_ids))
        .group_by(SupportMessage.thread_id)
    )
    msg_counts = dict(count_result.all())

    # Batch: last message per thread using DISTINCT ON
    last_msgs_result = await session.execute(
        select(SupportMessage)
        .where(SupportMessage.thread_id.in_(thread_ids))
        .order_by(SupportMessage.thread_id, SupportMessage.created_at.desc())
        .distinct(SupportMessage.thread_id)
    )
    last_msgs = {m.thread_id: m for m in last_msgs_result.scalars().all()}

    # Batch: user roles
    role_result = await session.execute(
        select(UserRole.user_id, Role.code)
        .join(Role)
        .where(UserRole.user_id.in_(user_ids))
        .where(UserRole.event_id == event_id)
    )
    user_roles = dict(role_result.all())

    items = []
    for t in threads:
        last_msg = last_msgs.get(t.id)
        unread = last_msg.sender_type == "user" if last_msg else False

        items.append(
            ThreadResponse(
                id=str(t.id),
                user_id=str(t.user_id),
                user_name=t.user.full_name or t.user.username or "N/A",
                user_username=t.user.username,
                user_role=user_roles.get(t.user_id),
                status=t.status,
                last_message=last_msg.text[:100] if last_msg else None,
                last_message_at=last_msg.created_at.isoformat() if last_msg else None,
                unread=unread,
                needs_attention=t.needs_attention,
                message_count=msg_counts.get(t.id, 0),
            )
        )

    return ThreadListResponse(threads=items, total=total)


async def get_messages(
    session: AsyncSession,
    thread_id: UUID,
    event_id: UUID,
    limit: int = 100,
    offset: int = 0,
) -> list[MessageResponse]:
    """Get messages in a thread. Verifies thread belongs to event."""
    thread = await session.get(SupportThread, thread_id)
    if not thread or thread.event_id != event_id:
        raise ValueError("Thread not found")

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
    event_id: UUID,
    organizer_id: UUID,
    text: str,
) -> SupportMessage:
    """Send organizer reply. Verifies thread belongs to event."""
    thread = await session.get(SupportThread, thread_id)
    if not thread or thread.event_id != event_id:
        raise ValueError("Thread not found")
    if thread.status != "open":
        raise ValueError("Thread is closed")

    msg = SupportMessage(
        thread_id=thread_id,
        sender_type="organizer",
        sender_id=organizer_id,
        text=text,
    )
    session.add(msg)
    thread.needs_attention = False
    thread.updated_at = datetime.now(timezone.utc)
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
    thread = await _get_or_create_open_thread(session, user_id, event_id)

    msg = SupportMessage(
        thread_id=thread.id,
        sender_type="organizer",
        sender_id=organizer_id,
        text=initial_message,
    )
    session.add(msg)
    thread.updated_at = datetime.now(timezone.utc)
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
    thread.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return thread


async def get_or_create_thread(
    session: AsyncSession,
    user_id: UUID,
    event_id: UUID,
) -> SupportThread:
    """Get open thread for user or create new one."""
    return await _get_or_create_open_thread(session, user_id, event_id)


async def _get_or_create_open_thread(
    session: AsyncSession,
    user_id: UUID,
    event_id: UUID,
) -> SupportThread:
    """Get or reopen existing thread. One thread per user per event."""
    # First: look for any thread (open or closed)
    result = await session.execute(
        select(SupportThread)
        .where(SupportThread.user_id == user_id)
        .where(SupportThread.event_id == event_id)
        .order_by(SupportThread.created_at.desc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    thread = result.scalar_one_or_none()
    if thread:
        if thread.status == "closed":
            thread.status = "open"
            thread.closed_by = None
            thread.updated_at = datetime.now(timezone.utc)
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
    """Add user message to thread. Stores raw text (no escaping)."""
    msg = SupportMessage(
        thread_id=thread_id,
        sender_type="user",
        sender_id=user_id,
        text=text,
    )
    session.add(msg)

    # Update thread timestamp
    thread = await session.get(SupportThread, thread_id)
    if thread:
        thread.updated_at = datetime.now(timezone.utc)

    await session.flush()
    await session.refresh(msg)
    return msg


async def get_unread_count(session: AsyncSession, event_id: UUID) -> int:
    """Count threads with last message from user. Single query, no N+1."""
    last_sender_subq = (
        select(SupportMessage.sender_type)
        .where(SupportMessage.thread_id == SupportThread.id)
        .order_by(SupportMessage.created_at.desc())
        .limit(1)
        .correlate(SupportThread)
        .scalar_subquery()
    )
    result = await session.execute(
        select(func.count())
        .select_from(SupportThread)
        .where(SupportThread.event_id == event_id)
        .where(SupportThread.status == "open")
        .where(last_sender_subq == "user")
    )
    return result.scalar() or 0


async def get_thread_messages_for_context(
    session: AsyncSession,
    thread_id: UUID,
) -> str:
    """Get full thread messages as text for AI agent context injection."""
    result = await session.execute(
        select(SupportMessage)
        .where(SupportMessage.thread_id == thread_id)
        .options(selectinload(SupportMessage.sender))
        .order_by(SupportMessage.created_at.asc())
        .limit(50)
    )
    messages = result.scalars().all()

    lines = []
    for m in messages:
        role_label = "Пользователь" if m.sender_type == "user" else "Организатор"
        name = m.sender.full_name or m.sender.username or "N/A"
        lines.append(f"[{role_label}] {name}: {m.text}")
    return "\n".join(lines)
