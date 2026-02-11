"""Reminder service for EPIC-007: DD Reminders.

Core logic for sending reminders to all roles before Demo Day.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.expert_room_assignment import ExpertRoomAssignment
from app.models.participation import ParticipationRequest, ParticipationStatus
from app.models.reminder import (
    NotificationStatus,
    RecipientType,
    ReminderBatch,
    ReminderBatchStatus,
    ReminderType,
)
from app.models.reminder import (
    ReminderNotification as Notification,
)
from app.models.room_project import RoomProject
from app.models.user import User
from app.services.admin import matching_service
from app.services.core.send_retry import MessageSender

logger = logging.getLogger(__name__)

# Rate limiting: 0.04s delay = ~25 msg/sec (safe under Telegram's 30 msg/sec)
SEND_DELAY = 0.04

# Telegram message limit is 4096 chars, use 4000 as safe threshold
MAX_MESSAGE_LENGTH = 4000


def truncate_message(text: str, max_len: int = MAX_MESSAGE_LENGTH) -> str:
    """Truncate message to fit Telegram limit, preserving complete lines.

    If text is under limit, returns as-is.
    Otherwise finds last complete line (project entry) before limit
    and adds "...и ещё N проектов" suffix.

    Uses character count (not bytes) as Telegram API counts UTF-8 characters.
    Ensures safe truncation at line boundaries to avoid breaking multi-byte chars.

    Args:
        text: Message text to truncate
        max_len: Maximum length (default 4000 for safety margin)

    Returns:
        Truncated text with suffix if needed
    """
    if not text:
        return text

    if len(text) <= max_len:
        return text

    # Count total project lines (lines starting with bullet or number)
    lines = text.split("\n")
    project_lines = [i for i, line in enumerate(lines) if _is_project_line(line)]
    total_projects = len(project_lines)

    if total_projects == 0:
        # No project lines found, simple truncation at word boundary
        logger.warning("Message truncation: no project lines found, using simple cut. Original length: %d", len(text))
        # Find last space before limit to avoid cutting words
        cut_point = max_len - 3
        while cut_point > 0 and text[cut_point] not in " \n\t":
            cut_point -= 1
        if cut_point == 0:
            cut_point = max_len - 3
        return text[:cut_point] + "..."

    # Reserve space for suffix "...и ещё NN проектов\n" (up to 30 chars)
    suffix_reserve = 30

    # Find how many lines we can keep (UTF-8 safe: we truncate at line boundaries)
    kept_lines = []
    current_len = 0
    kept_project_count = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len + suffix_reserve > max_len:
            break
        kept_lines.append(line)
        current_len += line_len
        if _is_project_line(line):
            kept_project_count += 1

    remaining = total_projects - kept_project_count
    if remaining > 0:
        suffix = f"\n...и ещё {remaining} проектов"
        result = "\n".join(kept_lines) + suffix
    else:
        result = "\n".join(kept_lines)

    logger.info(
        "Message truncated: %d → %d chars, kept %d/%d projects",
        len(text),
        len(result),
        kept_project_count,
        total_projects,
    )

    return result


def _is_project_line(line: str) -> bool:
    """Check if line is a project entry (starts with bullet, number, or emoji)."""
    stripped = line.strip()
    if not stripped:
        return False
    # Check for common project line patterns:
    # - "• Project name" or "- Project name"
    # - "1. Project name" or "1) Project name"
    # - "🔹 Project name" or similar emoji bullets
    first_char = stripped[0]
    return (
        first_char in "•-–—*▪▸►" or first_char.isdigit() or ord(first_char) > 0x1F000  # Emoji range
    )


async def check_duplicate(session: AsyncSession, event_id: UUID, reminder_type: ReminderType) -> dict | None:
    """Check if a reminder batch of same type was sent within 24h.

    Returns batch info if found, None otherwise.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    result = await session.execute(
        select(ReminderBatch)
        .where(ReminderBatch.event_id == event_id)
        .where(ReminderBatch.reminder_type == reminder_type)
        .where(ReminderBatch.status == ReminderBatchStatus.COMPLETED)
        .where(ReminderBatch.started_at > cutoff)
        .order_by(ReminderBatch.started_at.desc())
        .limit(1)
    )
    batch = result.scalars().first()

    if batch:
        minutes_ago = int((datetime.now(timezone.utc) - batch.started_at).total_seconds() / 60)
        return {
            "batch_id": str(batch.id),
            "minutes_ago": minutes_ago,
            "sent_count": batch.sent_count,
        }
    return None


async def get_student_recipients(session: AsyncSession, event_id: UUID) -> list[dict]:
    """Get students with room assignments for reminders.

    Returns list of dicts with user data, project, room, and acknowledgment status.
    """
    result = await session.execute(
        select(ParticipationRequest)
        .where(ParticipationRequest.event_id == event_id)
        .where(ParticipationRequest.room_project_id.isnot(None))
        .options(
            joinedload(ParticipationRequest.user),
            joinedload(ParticipationRequest.project),
            joinedload(ParticipationRequest.room_project).joinedload(RoomProject.room),
        )
    )
    requests = result.unique().scalars().all()

    recipients = []
    for pr in requests:
        if not pr.room_project:
            continue

        recipient = {
            "participation_id": str(pr.id),
            "project_title": pr.project.title if pr.project else "—",
            "room_name": pr.room_project.room.name if pr.room_project.room else "—",
            "acknowledged": pr.status == ParticipationStatus.ACKNOWLEDGED,
            "telegram_user_id": None,
            "user_id": None,
        }

        if pr.user:
            recipient["telegram_user_id"] = pr.user.telegram_user_id
            recipient["user_id"] = str(pr.user.id)

        recipients.append(recipient)

    return recipients


async def get_expert_recipients(session: AsyncSession, event_id: UUID, clustering_id: UUID | None = None) -> list[dict]:
    """Get experts with room assignments for reminders.

    Excludes declined experts. Returns list with expert data and room info.
    """
    if not clustering_id:
        clustering = await matching_service.get_approved_clustering(session, event_id)
        if not clustering:
            return []
        clustering_id = clustering.id

    result = await session.execute(
        select(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.clustering_run_id == clustering_id)
        .where(ExpertRoomAssignment.status != "declined")
        .options(
            selectinload(ExpertRoomAssignment.expert),
            selectinload(ExpertRoomAssignment.room),
        )
    )
    assignments = result.scalars().all()

    # Count projects per room
    room_project_counts = {}
    for a in assignments:
        if a.room_id not in room_project_counts:
            count_result = await session.execute(
                select(func.count(RoomProject.id)).where(RoomProject.room_id == a.room_id)
            )
            room_project_counts[a.room_id] = count_result.scalar() or 0

    recipients = []
    declined_count = 0

    for a in assignments:
        if a.status == "declined":
            declined_count += 1
            continue

        recipient = {
            "assignment_id": str(a.id),
            "expert_id": str(a.expert_id),
            "expert_name": a.expert.name if a.expert else "—",
            "room_name": a.room.name if a.room else "—",
            "room_id": str(a.room_id) if a.room_id else None,
            "project_count": room_project_counts.get(a.room_id, 0),
            "status": a.status,
            "telegram_chat_id": a.expert.telegram_chat_id if a.expert else None,
        }
        recipients.append(recipient)

    return recipients


async def get_guest_recipients(session: AsyncSession, event_id: UUID) -> list[dict]:
    """Get guests and business users for reminders.

    Returns list with user data and program placeholder.
    """
    result = await session.execute(select(User).where(User.guest_subtype.isnot(None)))
    users = result.scalars().all()

    recipients = []
    for user in users:
        recipient = {
            "user_id": str(user.id),
            "telegram_user_id": user.telegram_user_id,
            "full_name": user.full_name,
            "guest_subtype": user.guest_subtype.value if user.guest_subtype else None,
            "has_program": False,  # TODO: Check GuestProgram/Recommendation
        }
        recipients.append(recipient)

    return recipients


async def get_preview(session: AsyncSession, event_id: UUID, reminder_type: ReminderType) -> dict:
    """Get preview of reminder recipients by role.

    Aggregates all recipients, counts by role, detects skipped (no telegram),
    checks for duplicate batch.
    """
    # Get clustering for expert recipients
    clustering = await matching_service.get_approved_clustering(session, event_id)
    clustering_id = clustering.id if clustering else None

    # Get recipients by role
    students = await get_student_recipients(session, event_id)
    experts = await get_expert_recipients(session, event_id, clustering_id)
    guests = await get_guest_recipients(session, event_id)

    # Count with/without telegram
    students_with_tg = sum(1 for s in students if s.get("telegram_user_id"))
    students_without_tg = len(students) - students_with_tg

    experts_with_tg = sum(1 for e in experts if e.get("telegram_chat_id"))
    experts_without_tg = len(experts) - experts_with_tg

    # Separate guests and business
    guest_users = [g for g in guests if g.get("guest_subtype") != "business"]
    business_users = [g for g in guests if g.get("guest_subtype") == "business"]

    guests_with_tg = sum(1 for g in guest_users if g.get("telegram_user_id"))
    guests_without_tg = len(guest_users) - guests_with_tg

    business_with_tg = sum(1 for b in business_users if b.get("telegram_user_id"))
    business_without_tg = len(business_users) - business_with_tg

    # Check for duplicate
    duplicate = await check_duplicate(session, event_id, reminder_type)

    total_recipients = students_with_tg + experts_with_tg + guests_with_tg + business_with_tg
    total_skipped = students_without_tg + experts_without_tg + guests_without_tg + business_without_tg

    return {
        "reminder_type": reminder_type,
        "by_role": {
            "students": {"count": students_with_tg, "skipped": students_without_tg},
            "experts": {"count": experts_with_tg, "skipped": experts_without_tg, "declined": 0},
            "guests": {"count": guests_with_tg, "skipped": guests_without_tg},
            "business": {"count": business_with_tg, "skipped": business_without_tg},
        },
        "total_recipients": total_recipients,
        "total_skipped": total_skipped,
        "duplicate_warning": duplicate,
    }


async def create_batch(
    session: AsyncSession,
    event_id: UUID,
    reminder_type: ReminderType,
    initiated_by: str,
    initiated_by_name: str | None = None,
    total_recipients: int = 0,
) -> ReminderBatch:
    """Create a new reminder batch with status=confirmed.

    Returns the created batch.
    """
    batch = ReminderBatch(
        event_id=event_id,
        reminder_type=reminder_type,
        initiated_by=initiated_by,
        initiated_by_name=initiated_by_name,
        total_recipients=total_recipients,
        status=ReminderBatchStatus.CONFIRMED,
        started_at=datetime.now(timezone.utc),
    )
    session.add(batch)
    await session.flush()
    return batch


async def execute_batch(
    session: AsyncSession, batch: ReminderBatch, bot: MessageSender, event_id: UUID
) -> ReminderBatch:
    """Execute a reminder batch - send all notifications.

    Updates batch with sent/failed/skipped counts and completion time.
    """
    batch.status = ReminderBatchStatus.IN_PROGRESS
    await session.flush()

    total_sent = 0
    total_failed = 0

    # Send to students
    sent, failed = await send_student_reminders(session, batch, bot, batch.reminder_type, event_id)
    total_sent += sent
    total_failed += failed

    # Send to experts
    sent, failed = await send_expert_reminders(session, batch, bot, batch.reminder_type, event_id)
    total_sent += sent
    total_failed += failed

    # Send to guests (includes business)
    sent, failed = await send_guest_reminders(session, batch, bot, batch.reminder_type, event_id)
    total_sent += sent
    total_failed += failed

    batch.sent_count = total_sent
    batch.failed_count = total_failed
    batch.status = ReminderBatchStatus.COMPLETED
    batch.completed_at = datetime.now(timezone.utc)
    await session.commit()

    return batch


# Message formatting functions


def format_student_day_before(project_title: str, room_name: str, event_date: str, acknowledged: bool) -> str:
    """Format day-before message for student."""
    msg = f"📅 Завтра ты выступаешь!\n\nПроект: {project_title}\nЗал: {room_name}\nДата: {event_date}\n"
    if not acknowledged:
        msg += "\n⚠️ Пожалуйста, подтвердите участие."
    return msg


def format_expert_day_before(room_name: str, project_count: int) -> str:
    """Format day-before message for expert."""
    return f"📅 Завтра Demo Day!\n\nЗал: {room_name}\nПроектов: {project_count}\n\nЖдём вас для оценки проектов!"


def format_guest_day_before(full_name: str, has_program: bool, projects: list[dict] | None = None) -> str:
    """Format day-before message for guest.

    Args:
        full_name: Guest's full name
        has_program: Whether guest has a personal program
        projects: List of project dicts with 'title' and optionally 'room_name'

    Returns:
        Formatted message, truncated if needed
    """
    if not has_program or not projects:
        return "📅 Завтра Demo Day!\n\nПройдите профилирование, чтобы получить персональную программу."

    # Build message with project list
    lines = [
        "📅 Завтра Demo Day!",
        "",
        "Ваша персональная программа:",
        "",
    ]

    for i, proj in enumerate(projects, 1):
        room = proj.get("room_name", "")
        room_suffix = f" ({room})" if room else ""
        lines.append(f"{i}. {proj['title']}{room_suffix}")

    lines.append("")
    lines.append("До встречи!")

    text = "\n".join(lines)
    return truncate_message(text)


def format_business_day_before(full_name: str, has_program: bool, projects: list[dict] | None = None) -> str:
    """Format day-before message for business partner.

    Args:
        full_name: Business partner's full name
        has_program: Whether they have a personal program
        projects: List of project dicts with 'title' and optionally 'room_name'

    Returns:
        Formatted message, truncated if needed
    """
    if not has_program or not projects:
        return "📅 Завтра Demo Day!\n\nПройдите профилирование, чтобы получить персональную подборку проектов."

    # Build message with project list
    lines = [
        "📅 Завтра Demo Day!",
        "",
        "Ваша персональная подборка проектов:",
        "",
    ]

    for i, proj in enumerate(projects, 1):
        room = proj.get("room_name", "")
        room_suffix = f" ({room})" if room else ""
        lines.append(f"{i}. {proj['title']}{room_suffix}")

    lines.append("")
    lines.append("До встречи!")

    text = "\n".join(lines)
    return truncate_message(text)


def format_student_hour_before(project_title: str, room_name: str) -> str:
    """Format hour-before message for student."""
    return f"⏰ Через час — твоё выступление!\n\nЗал: {room_name}\nПроект: {project_title}\n\nУдачи! 🎯"


def format_expert_hour_before(room_name: str, first_project: str | None) -> str:
    """Format hour-before message for expert."""
    msg = f"⏰ Через час — начало!\n\nЗал: {room_name}\n"
    if first_project:
        msg += f"Первый проект: {first_project}\n"
    msg += "\nЖдём вас!"
    return msg


def format_guest_hour_before(full_name: str) -> str:
    """Format hour-before message for guest."""
    return "⏰ DD начинается через час!\n\nЖдём вас!"


# Sending functions


async def send_student_reminders(
    session: AsyncSession,
    batch: ReminderBatch,
    bot: MessageSender,
    reminder_type: ReminderType,
    event_id: UUID,
) -> tuple[int, int]:
    """Send reminders to students. Returns (sent_count, failed_count)."""
    from app.services.core import user_service

    event = await user_service.get_current_event(session)
    event_date = event.start_date.strftime("%d.%m.%Y") if event else "—"

    students = await get_student_recipients(session, event_id)

    sent = 0
    failed = 0

    for student in students:
        tg_id = student.get("telegram_user_id")
        if not tg_id:
            continue

        # Format message based on type
        if reminder_type == ReminderType.DAY_BEFORE:
            text = format_student_day_before(
                student["project_title"],
                student["room_name"],
                event_date,
                student["acknowledged"],
            )
        else:
            text = format_student_hour_before(
                student["project_title"],
                student["room_name"],
            )

        # T028: Handle empty message edge case
        if not text or not text.strip():
            logger.warning("Empty message for student %s, skipping", tg_id)
            notification = Notification(
                batch_id=batch.id,
                recipient_type=RecipientType.STUDENT,
                telegram_user_id=tg_id,
                participation_id=UUID(student["participation_id"]),
                status=NotificationStatus.SKIPPED,
                message_text="",
            )
            session.add(notification)
            continue

        # Create notification record
        notification = Notification(
            batch_id=batch.id,
            recipient_type=RecipientType.STUDENT,
            telegram_user_id=tg_id,
            participation_id=UUID(student["participation_id"]),
            status=NotificationStatus.PENDING,
            message_text=text,
        )
        session.add(notification)

        try:
            await bot.send_message(chat_id=int(tg_id), text=text)
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)
            sent += 1
        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)[:500]
            failed += 1
            logger.warning("Failed to send student reminder to %s: %s", tg_id, e)

        await asyncio.sleep(SEND_DELAY)

    await session.flush()
    return sent, failed


async def send_expert_reminders(
    session: AsyncSession,
    batch: ReminderBatch,
    bot: MessageSender,
    reminder_type: ReminderType,
    event_id: UUID,
) -> tuple[int, int]:
    """Send reminders to experts. Returns (sent_count, failed_count)."""
    experts = await get_expert_recipients(session, event_id)

    sent = 0
    failed = 0

    for expert in experts:
        tg_id = expert.get("telegram_chat_id")
        if not tg_id:
            continue

        # Format message based on type
        if reminder_type == ReminderType.DAY_BEFORE:
            text = format_expert_day_before(
                expert["room_name"],
                expert["project_count"],
            )
        else:
            text = format_expert_hour_before(
                expert["room_name"],
                None,  # TODO: Get first project name
            )

        # T028: Handle empty message edge case
        if not text or not text.strip():
            logger.warning("Empty message for expert %s, skipping", tg_id)
            notification = Notification(
                batch_id=batch.id,
                recipient_type=RecipientType.EXPERT,
                telegram_user_id=tg_id,
                expert_id=UUID(expert["expert_id"]),
                status=NotificationStatus.SKIPPED,
                message_text="",
            )
            session.add(notification)
            continue

        # Create notification record
        notification = Notification(
            batch_id=batch.id,
            recipient_type=RecipientType.EXPERT,
            telegram_user_id=tg_id,
            expert_id=UUID(expert["expert_id"]),
            status=NotificationStatus.PENDING,
            message_text=text,
        )
        session.add(notification)

        try:
            await bot.send_message(chat_id=int(tg_id), text=text)
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)
            sent += 1
        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)[:500]
            failed += 1
            logger.warning("Failed to send expert reminder to %s: %s", tg_id, e)

        await asyncio.sleep(SEND_DELAY)

    await session.flush()
    return sent, failed


async def send_guest_reminders(
    session: AsyncSession,
    batch: ReminderBatch,
    bot: MessageSender,
    reminder_type: ReminderType,
    event_id: UUID,
) -> tuple[int, int]:
    """Send reminders to guests and business. Returns (sent_count, failed_count)."""
    guests = await get_guest_recipients(session, event_id)

    sent = 0
    failed = 0

    for guest in guests:
        tg_id = guest.get("telegram_user_id")
        if not tg_id:
            continue

        is_business = guest.get("guest_subtype") == "business"
        recipient_type = RecipientType.BUSINESS if is_business else RecipientType.GUEST

        # Get guest program if day-before
        projects = None
        if reminder_type == ReminderType.DAY_BEFORE and guest["has_program"]:
            projects = await get_guest_program(session, UUID(guest["user_id"]))

        # Format message based on type and role
        if reminder_type == ReminderType.DAY_BEFORE:
            if is_business:
                text = format_business_day_before(guest["full_name"], guest["has_program"], projects)
            else:
                text = format_guest_day_before(guest["full_name"], guest["has_program"], projects)
        else:
            text = format_guest_hour_before(guest["full_name"])

        # T028: Handle empty message edge case
        if not text or not text.strip():
            logger.warning("Empty message for guest %s, skipping", tg_id)
            notification = Notification(
                batch_id=batch.id,
                recipient_type=recipient_type,
                telegram_user_id=tg_id,
                user_id=UUID(guest["user_id"]),
                status=NotificationStatus.SKIPPED,
                message_text="",
            )
            session.add(notification)
            continue

        # Create notification record
        notification = Notification(
            batch_id=batch.id,
            recipient_type=recipient_type,
            telegram_user_id=tg_id,
            user_id=UUID(guest["user_id"]),
            status=NotificationStatus.PENDING,
            message_text=text,
        )
        session.add(notification)

        try:
            await bot.send_message(chat_id=int(tg_id), text=text)
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)
            sent += 1
        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)[:500]
            failed += 1
            logger.warning("Failed to send guest reminder to %s: %s", tg_id, e)

        await asyncio.sleep(SEND_DELAY)

    await session.flush()
    return sent, failed


async def get_guest_program(session: AsyncSession, user_id: UUID) -> list[dict]:
    """Fetch saved program for guest/business user."""
    # TODO: T030 - Query GuestProgram or Recommendations
    return []


async def get_interrupted_batch(session: AsyncSession, event_id: UUID) -> ReminderBatch | None:
    """Find the newest interrupted (in_progress) batch for event.

    Returns the most recent batch with status=in_progress, or None if none found.
    Used for batch recovery flow (EPIC-007b US2).
    """
    result = await session.execute(
        select(ReminderBatch)
        .where(ReminderBatch.event_id == event_id)
        .where(ReminderBatch.status == ReminderBatchStatus.IN_PROGRESS)
        .order_by(ReminderBatch.started_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def resume_batch(session: AsyncSession, batch: ReminderBatch, bot: MessageSender) -> ReminderBatch:
    """Resume an interrupted batch - send only pending notifications.

    Queries notifications with status != sent and continues sending.
    Returns updated batch with final counts.
    """
    logger.info("Resuming batch %s, started at %s", batch.id, batch.started_at)

    # Get pending notifications
    result = await session.execute(
        select(Notification)
        .where(Notification.batch_id == batch.id)
        .where(Notification.status != NotificationStatus.SENT)
    )
    pending_notifications = result.scalars().all()

    logger.info("Found %d pending notifications to resume", len(pending_notifications))

    sent = batch.sent_count or 0
    failed = batch.failed_count or 0

    for notification in pending_notifications:
        tg_id = notification.telegram_user_id
        text = notification.message_text

        if not text:
            notification.status = NotificationStatus.SKIPPED
            continue

        try:
            await bot.send_message(chat_id=int(tg_id), text=text)
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)
            sent += 1
        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)[:500]
            failed += 1
            logger.warning("Failed to send resumed notification to %s: %s", tg_id, e)

        await asyncio.sleep(SEND_DELAY)

    batch.sent_count = sent
    batch.failed_count = failed
    batch.status = ReminderBatchStatus.COMPLETED
    batch.completed_at = datetime.now(timezone.utc)
    await session.commit()

    logger.info("Batch %s resumed: sent=%d, failed=%d", batch.id, sent, failed)
    return batch


async def cancel_batch(session: AsyncSession, batch: ReminderBatch) -> ReminderBatch:
    """Cancel an interrupted batch by setting status to cancelled."""
    logger.info("Cancelling batch %s", batch.id)
    batch.status = ReminderBatchStatus.CANCELLED
    batch.completed_at = datetime.now(timezone.utc)
    await session.commit()
    return batch
