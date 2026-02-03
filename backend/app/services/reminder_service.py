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
from telegram import Bot

from app.models.expert import Expert
from app.models.expert_room_assignment import ExpertRoomAssignment
from app.models.participation import ParticipationRequest, ParticipationStatus
from app.models.reminder import (
    Notification,
    NotificationStatus,
    RecipientType,
    ReminderBatch,
    ReminderBatchStatus,
    ReminderType,
)
from app.models.room import Room
from app.models.room_project import RoomProject
from app.models.user import User
from app.services import matching_service

logger = logging.getLogger(__name__)

# Rate limiting: 0.04s delay = ~25 msg/sec (safe under Telegram's 30 msg/sec)
SEND_DELAY = 0.04


async def check_duplicate(
    session: AsyncSession, event_id: UUID, reminder_type: ReminderType
) -> dict | None:
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


async def get_expert_recipients(
    session: AsyncSession, event_id: UUID, clustering_id: UUID | None = None
) -> list[dict]:
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
                select(func.count(RoomProject.id))
                .where(RoomProject.room_id == a.room_id)
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
    result = await session.execute(
        select(User)
        .where(User.guest_subtype.isnot(None))
    )
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


async def get_preview(
    session: AsyncSession, event_id: UUID, reminder_type: ReminderType
) -> dict:
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
    session: AsyncSession, batch: ReminderBatch, bot: Bot, event_id: UUID
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
    msg = (
        f"📅 Завтра ты выступаешь!\n\n"
        f"Проект: {project_title}\n"
        f"Зал: {room_name}\n"
        f"Дата: {event_date}\n"
    )
    if not acknowledged:
        msg += "\n⚠️ Пожалуйста, подтвердите участие."
    return msg


def format_expert_day_before(room_name: str, project_count: int) -> str:
    """Format day-before message for expert."""
    return (
        f"📅 Завтра Demo Day!\n\n"
        f"Зал: {room_name}\n"
        f"Проектов: {project_count}\n\n"
        f"Ждём вас для оценки проектов!"
    )


def format_guest_day_before(full_name: str, has_program: bool) -> str:
    """Format day-before message for guest."""
    if has_program:
        return (
            f"📅 Завтра Demo Day!\n\n"
            f"Ваша персональная программа готова.\n"
            f"До встречи!"
        )
    return (
        f"📅 Завтра Demo Day!\n\n"
        f"Пройдите профилирование, чтобы получить персональную программу."
    )


def format_business_day_before(full_name: str, has_program: bool) -> str:
    """Format day-before message for business partner."""
    if has_program:
        return (
            f"📅 Завтра Demo Day!\n\n"
            f"Ваша персональная подборка проектов готова.\n"
            f"До встречи!"
        )
    return (
        f"📅 Завтра Demo Day!\n\n"
        f"Пройдите профилирование, чтобы получить персональную подборку проектов."
    )


def format_student_hour_before(project_title: str, room_name: str) -> str:
    """Format hour-before message for student."""
    return (
        f"⏰ Через час — твоё выступление!\n\n"
        f"Зал: {room_name}\n"
        f"Проект: {project_title}\n\n"
        f"Удачи! 🎯"
    )


def format_expert_hour_before(room_name: str, first_project: str | None) -> str:
    """Format hour-before message for expert."""
    msg = f"⏰ Через час — начало!\n\nЗал: {room_name}\n"
    if first_project:
        msg += f"Первый проект: {first_project}\n"
    msg += "\nЖдём вас!"
    return msg


def format_guest_hour_before(full_name: str) -> str:
    """Format hour-before message for guest."""
    return (
        f"⏰ DD начинается через час!\n\n"
        f"Ждём вас!"
    )


# Sending functions


async def send_student_reminders(
    session: AsyncSession,
    batch: ReminderBatch,
    bot: Bot,
    reminder_type: ReminderType,
    event_id: UUID,
) -> tuple[int, int]:
    """Send reminders to students. Returns (sent_count, failed_count)."""
    from app.services import user_service

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
    bot: Bot,
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
    bot: Bot,
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

        # Format message based on type and role
        if reminder_type == ReminderType.DAY_BEFORE:
            if is_business:
                text = format_business_day_before(guest["full_name"], guest["has_program"])
            else:
                text = format_guest_day_before(guest["full_name"], guest["has_program"])
        else:
            text = format_guest_hour_before(guest["full_name"])

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
