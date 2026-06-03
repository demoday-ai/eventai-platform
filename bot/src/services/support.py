import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.sanitize import sanitize_text
from src.models.chat_message import ChatMessage
from src.models.support_log import SupportLog
from src.models.support_thread import SupportThread

logger = logging.getLogger(__name__)


async def is_taken_over(db: AsyncSession, user_id: UUID, event_id: UUID) -> bool:
    """True if an organizer has taken over this conversation (AI must stay silent)."""
    row = (
        await db.execute(
            select(SupportThread.taken_over)
            .where(
                SupportThread.user_id == user_id,
                SupportThread.event_id == event_id,
            )
            .order_by(SupportThread.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return bool(row)


async def _get_or_create_open_thread(
    db: AsyncSession, user_id: UUID, event_id: UUID
) -> SupportThread:
    """Get the user's thread for the event (reopen if closed) or create one.

    One thread per user per event (matches backend unique constraint).
    """
    result = await db.execute(
        select(SupportThread)
        .where(SupportThread.user_id == user_id, SupportThread.event_id == event_id)
        .order_by(SupportThread.created_at.desc())
        .limit(1)
        # Lock the row so two concurrent guest messages don't both fall through
        # to INSERT and violate UNIQUE(user_id, event_id) (migration 035).
        .with_for_update(skip_locked=False)
    )
    thread = result.scalar_one_or_none()
    if thread:
        if thread.status == "closed":
            thread.status = "open"
            thread.closed_by = None
            thread.updated_at = datetime.now(timezone.utc)
        return thread

    thread = SupportThread(user_id=user_id, event_id=event_id, status="open")
    db.add(thread)
    await db.flush()
    return thread


async def add_user_support_message(
    db: AsyncSession,
    user_id: UUID,
    event_id: UUID,
    text: str,
) -> ChatMessage:
    """Persist a guest support message into chat_messages (single source of truth).

    Reuses/reopens the user's thread and flags it as needing organizer attention;
    the message itself goes to chat_messages (role=user), which the web admin reads.
    """
    thread = await _get_or_create_open_thread(db, user_id, event_id)
    thread.needs_attention = True
    thread.updated_at = datetime.now(timezone.utc)

    msg = ChatMessage(
        user_id=user_id,
        event_id=event_id,
        role="user",
        content=(sanitize_text(text) or "")[:1000],
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg


async def get_support_history(
    db: AsyncSession,
    user_id: UUID,
    event_id: UUID,
    limit: int = 20,
) -> list[str] | None:
    """Render recent conversation lines (chat_messages) for AI agent context.

    Takes the NEWEST `limit` messages (so the latest organizer answer is never
    dropped), id as tiebreaker for deterministic order, rendered chronologically.
    """
    messages = (
        await db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.event_id == event_id,
            )
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit)
        )
    ).scalars().all()
    if not messages:
        return None

    label = {"user": "Пользователь", "assistant": "Ассистент", "organizer": "Организатор"}
    lines: list[str] = []
    for m in reversed(messages):
        lines.append(f"{label.get(m.role, m.role)}: {m.content}")
    return lines


def generate_correlation_id() -> str:
    """Generate short correlation ID: SQ-<6 hex chars>."""
    return f"SQ-{secrets.token_hex(3)}"


async def create_support_entry(
    db: AsyncSession,
    user_id: UUID,
    event_id: UUID,
    question: str,
) -> SupportLog:
    """Create support log entry with correlation_id."""
    entry = SupportLog(
        user_id=user_id,
        event_id=event_id,
        correlation_id=generate_correlation_id(),
        question=(sanitize_text(question) or "")[:1000],  # max 1000 chars
    )
    db.add(entry)
    await db.flush()
    return entry


async def find_by_correlation_id(
    db: AsyncSession, correlation_id: str
) -> SupportLog | None:
    result = await db.execute(
        select(SupportLog).where(
            SupportLog.correlation_id == correlation_id,
            SupportLog.answer.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def find_by_bot_message_id(
    db: AsyncSession, bot_message_id: int
) -> SupportLog | None:
    """Find support log by the bot's message ID in organizer group (for reply_to).

    Searches unanswered entries created within the last 24 hours, ordered by
    most recent first. The bot_message_id is matched against the correlation_id
    field where the message ID was stored after forwarding to the organizer group.
    """
    cutoff = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(SupportLog)
        .where(
            SupportLog.answer.is_(None),
            SupportLog.created_at >= cutoff,
        )
        .order_by(SupportLog.created_at.desc())
    )
    # Linear scan over recent unanswered entries to find matching message_id
    # stored in correlation_id after forwarding
    for entry in result.scalars().all():
        if entry.correlation_id == str(bot_message_id):
            return entry
    return None


async def save_answer(
    db: AsyncSession,
    entry: SupportLog,
    answer: str,
) -> None:
    entry.answer = answer
    entry.answered_at = datetime.now(timezone.utc)
    await db.flush()
