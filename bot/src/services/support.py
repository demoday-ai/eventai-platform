import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.sanitize import sanitize_text
from src.models.support_log import SupportLog
from src.models.support_message import SupportMessage
from src.models.support_thread import SupportThread

logger = logging.getLogger(__name__)


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
) -> SupportMessage:
    """Persist a guest support message into the unified thread model (ADR-001).

    Reuses/reopens the user's thread, appends a "user" message, flags the
    thread as needing organizer attention. The web admin reads the same tables.
    """
    thread = await _get_or_create_open_thread(db, user_id, event_id)
    thread.needs_attention = True
    thread.updated_at = datetime.now(timezone.utc)

    msg = SupportMessage(
        thread_id=thread.id,
        sender_type="user",
        sender_id=user_id,
        text=(sanitize_text(text) or "")[:1000],
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
    """Render the user's support thread as text lines for AI agent context.

    Returns None if the user has no thread. Lines look like
    "Пользователь: ..." / "Организатор: ..." in chronological order.
    """
    thread = (
        await db.execute(
            select(SupportThread)
            .where(
                SupportThread.user_id == user_id,
                SupportThread.event_id == event_id,
            )
            .order_by(SupportThread.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not thread:
        return None

    # Take the NEWEST `limit` messages (so the latest organizer answer is never
    # dropped), with id as a tiebreaker for deterministic order when several
    # messages share an identical created_at; then render chronologically.
    messages = (
        await db.execute(
            select(SupportMessage)
            .where(SupportMessage.thread_id == thread.id)
            .order_by(
                SupportMessage.created_at.desc(),
                SupportMessage.id.desc(),
            )
            .limit(limit)
        )
    ).scalars().all()
    if not messages:
        return None

    lines: list[str] = []
    for m in reversed(messages):
        label = "Пользователь" if m.sender_type == "user" else "Организатор"
        lines.append(f"{label}: {m.text}")
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
