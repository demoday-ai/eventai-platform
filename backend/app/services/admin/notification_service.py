"""Notification service - delivery engine, reminders, batching, escalations."""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytz
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ClusteringRun,
    Escalation,
    Event,
    ExpertRoomAssignment,
    Notification,
    NotificationStatus,
    NotificationType,
    Role,
    RoleCode,
    Room,
    ScheduleChangeLog,
    ScheduleSlot,
    SlotStatus,
    User,
    UserRole,
)
from app.schemas.schedule import (
    NotificationDashboard,
    NotificationItem,
    NotificationListResponse,
    RecipientCounts,
    ReminderPreview,
    ReminderSendResult,
    RoleStats,
    SampleMessages,
    StatusSummary,
    TypeStats,
    UnreachableParticipant,
)

logger = logging.getLogger(__name__)
MSK = pytz.timezone("Europe/Moscow")

# Throttling: max 25 concurrent sends, 0.05s delay between
SEND_SEMAPHORE_LIMIT = 25
SEND_DELAY_SECONDS = 0.05
MAX_RETRIES = 3
TELEGRAM_MAX_LENGTH = 4096


class CancellationWindowClosedError(Exception):
    """Raised when trying to cancel reminders after the deadline."""

    pass


# ========== Core Delivery Engine (T009) ==========


async def send_notification(
    session: AsyncSession,
    notification_id: UUID,
    bot,
) -> bool:
    """
    Send a single notification via Telegram.

    Returns True if sent successfully, False otherwise.
    """
    result = await session.execute(
        select(Notification).where(Notification.id == notification_id).options(selectinload(Notification.user))
    )
    notification = result.scalars().first()

    if not notification:
        logger.warning("Notification %s not found", notification_id)
        return False

    if notification.status not in (NotificationStatus.PENDING.value, NotificationStatus.FAILED.value):
        logger.debug("Notification %s already processed (status=%s)", notification_id, notification.status)
        return False

    user = notification.user
    if not user or not user.telegram_user_id:
        notification.status = NotificationStatus.FAILED.value
        notification.error_message = "User has no telegram_user_id"
        notification.retry_count += 1
        await session.commit()
        return False

    try:
        await bot.send_message(
            chat_id=user.telegram_user_id,
            text=notification.content[:TELEGRAM_MAX_LENGTH],
        )
        notification.status = NotificationStatus.SENT.value
        notification.sent_at = datetime.now(timezone.utc)
        notification.error_message = None
        await session.commit()
        logger.info("Notification %s sent to user %s", notification_id, user.id)
        return True

    except Exception as e:
        notification.retry_count += 1
        notification.error_message = str(e)[:500]

        if notification.retry_count >= MAX_RETRIES:
            notification.status = NotificationStatus.FAILED.value
            logger.warning("Notification %s failed after %d retries: %s", notification_id, MAX_RETRIES, e)
        else:
            logger.info(
                "Notification %s failed (retry %d/%d): %s", notification_id, notification.retry_count, MAX_RETRIES, e
            )

        await session.commit()
        return False


async def send_bulk_notifications(
    session: AsyncSession,
    notification_ids: list[UUID],
    bot,
) -> tuple[int, int]:
    """
    Send multiple notifications with throttling.

    Returns (sent_count, failed_count).
    """
    semaphore = asyncio.Semaphore(SEND_SEMAPHORE_LIMIT)
    sent = 0
    failed = 0

    async def send_with_throttle(nid: UUID):
        nonlocal sent, failed
        async with semaphore:
            success = await send_notification(session, nid, bot)
            if success:
                sent += 1
            else:
                failed += 1
            await asyncio.sleep(SEND_DELAY_SECONDS)

    tasks = [send_with_throttle(nid) for nid in notification_ids]
    await asyncio.gather(*tasks)

    return sent, failed


async def retry_failed(
    session: AsyncSession,
    event_id: UUID,
    bot,
) -> tuple[int, int]:
    """
    Retry failed notifications with retry_count < 3.

    Uses exponential backoff (2^retry_count seconds).
    """
    result = await session.execute(
        select(Notification)
        .where(Notification.event_id == event_id)
        .where(Notification.status == NotificationStatus.FAILED.value)
        .where(Notification.retry_count < MAX_RETRIES)
    )
    notifications = list(result.scalars().all())

    if not notifications:
        return 0, 0

    sent = 0
    failed = 0

    for n in notifications:
        # Exponential backoff
        backoff = 2**n.retry_count
        await asyncio.sleep(backoff)

        success = await send_notification(session, n.id, bot)
        if success:
            sent += 1
        else:
            failed += 1

    return sent, failed


# ========== Escalation Integration (T010) ==========


async def create_notification_escalation(
    session: AsyncSession,
    notification: Notification,
    event_id: UUID,
) -> Escalation | None:
    """
    Create escalation when notification fails permanently or user unreachable.

    Escalation types:
    - notification_undeliverable: user never started bot
    - reminder_send_failed: Telegram API error after 3 retries
    """
    user = notification.user

    if not user:
        # Reload user
        result = await session.execute(select(User).where(User.id == notification.user_id))
        user = result.scalars().first()

    if not user:
        return None

    # Determine escalation type
    user_label = user.full_name or user.username or str(user.id)
    if not user.telegram_user_id:
        esc_type = "notification_undeliverable"
        message = f"Пользователь {user_label} не запустил бот (нет telegram_user_id)"
    else:
        esc_type = "reminder_send_failed"
        message = (
            f"Не удалось отправить уведомление пользователю {user_label}:"
            f" {notification.error_message or 'Unknown error'}"
        )

    # Check if escalation already exists
    existing = await session.execute(
        select(Escalation)
        .where(Escalation.event_id == event_id)
        .where(Escalation.type == esc_type)
        .where(Escalation.resolved is False)
    )
    if existing.scalars().first():
        return None

    # Create escalation - need to find a room for context
    # Get room from schedule slot if available
    room_id = None
    if notification.schedule_slot_id:
        slot_result = await session.execute(
            select(ScheduleSlot).where(ScheduleSlot.id == notification.schedule_slot_id)
        )
        slot = slot_result.scalars().first()
        if slot:
            room_id = slot.room_id

    # If no room, get any room from event
    if not room_id:
        room_result = await session.execute(
            select(Room).join(ClusteringRun).where(ClusteringRun.event_id == event_id).limit(1)
        )
        room = room_result.scalars().first()
        if room:
            room_id = room.id

    if not room_id:
        logger.warning("Cannot create escalation: no room found for event %s", event_id)
        return None

    # For EPIC-004 compatibility, escalation needs expert_id
    # We'll create a pseudo-escalation without expert if user is not an expert
    # Actually, looking at the Escalation model, expert_id is required
    # So we need to either:
    # 1. Make expert_id nullable in the model
    # 2. Find or create an expert record
    # For now, let's just log and skip if not an expert

    # Check if user has expert role
    expert_result = await session.execute(
        select(UserRole).join(Role).where(UserRole.user_id == user.id).where(Role.code == RoleCode.EXPERT.value)
    )
    is_expert = expert_result.scalars().first() is not None

    if not is_expert:
        # Log but don't create escalation (EPIC-004 model limitation)
        logger.info("Notification escalation for non-expert user %s (type=%s): %s", user.id, esc_type, message)
        return None

    # Get expert record
    from app.models import Expert

    expert_result = await session.execute(select(Expert).where(Expert.user_id == user.id))
    expert = expert_result.scalars().first()

    if not expert:
        logger.warning("User %s has expert role but no Expert record", user.id)
        return None

    escalation = Escalation(
        expert_id=expert.id,
        room_id=room_id,
        event_id=event_id,
        type=esc_type,
        message=message,
    )
    session.add(escalation)
    await session.commit()

    return escalation


# ========== Reminder Message Templates (T011) ==========


def build_eve_reminder(
    user: User,
    role: str,
    schedule_data: dict,
    event: Event,
) -> str:
    """
    Build personalized eve-of-DD reminder message.

    Args:
        user: The recipient user
        role: User role (student, expert, guest, business)
        schedule_data: Role-specific schedule information
        event: The event

    Returns:
        Formatted message text in Russian
    """
    event_name = event.name if event else "Demo Day"
    event_date = schedule_data.get("date", "")
    if isinstance(event_date, date):
        event_date = event_date.strftime("%d.%m.%Y")

    if role == "student":
        room_name = schedule_data.get("room_name", "...")
        time_str = schedule_data.get("time", "...")
        return f"🎓 Завтра {event_name}!\n\nТы выступаешь в {room_name}, время {time_str}.\n\nУдачи! 🍀"

    elif role == "expert":
        room_name = schedule_data.get("room_name", "...")
        time_str = schedule_data.get("time", "...")
        projects = schedule_data.get("projects", [])
        projects_text = "\n".join(f"• {p}" for p in projects[:10])
        if len(projects) > 10:
            projects_text += f"\n... и ещё {len(projects) - 10} проектов"

        return (
            f"👨‍🏫 Завтра {event_name}!\n\n"
            f"Ваша комната: {room_name}\n"
            f"Время: {time_str}\n\n"
            f"Проекты, которые вы будете оценивать:\n{projects_text}"
        )

    elif role in ("guest", "business"):
        program = schedule_data.get("program", [])
        if not program:
            return f"🎉 Завтра {event_name}!\n\nИспользуйте /program чтобы получить персональную подборку проектов."

        program_text = "\n".join(
            f"• {p.get('time', '...')} — {p.get('project', '...')} ({p.get('room', '...')})" for p in program[:15]
        )
        if len(program) > 15:
            program_text += f"\n... и ещё {len(program) - 15} проектов"

        icon = "💼" if role == "business" else "👤"
        return f"{icon} Завтра {event_name}!\n\nВаша персональная программа:\n{program_text}"

    else:
        return f"🎉 Завтра {event_name}!\n\nИспользуйте /program для просмотра расписания."


def build_pre_slot_reminder(
    user: User,
    role: str,
    schedule_slot: ScheduleSlot,
    room: Room | None = None,
    project_title: str | None = None,
) -> str:
    """Build 30-min-before reminder message for all roles."""
    room_name = room.name if room else "..."

    if role == "student":
        return f"⏰ Через 30 минут - твое выступление в {room_name}!"

    elif role == "expert":
        return f"⏰ Через 30 минут - начало оценки в {room_name}!"

    elif role in ("guest", "business"):
        project = project_title or "проект"
        return f"⏰ Через 30 минут - {project} в {room_name}!"

    else:
        return f"⏰ Через 30 минут - событие в {room_name}!"


# ========== Eve-of-DD Reminder Job (T012) ==========


async def send_eve_reminders(
    session: AsyncSession,
    event_id: UUID,
    target_day: date,
    bot,
) -> ReminderSendResult:
    """
    Send eve-of-DD reminders to all participants for a specific day.
    """
    # Get event
    event_result = await session.execute(select(Event).where(Event.id == event_id))
    event = event_result.scalars().first()
    if not event:
        raise ValueError("Event not found")

    # Check schedule is approved
    from app.services.admin import schedule_service

    if not await schedule_service.is_schedule_approved(session, event_id):
        raise ValueError("Schedule not approved")

    sent_count = 0
    failed_count = 0
    skipped_count = 0
    notification_ids = []

    scheduled_date = target_day - timedelta(days=1)

    # Get all users with roles for this event
    users_result = await session.execute(
        select(User)
        .join(UserRole)
        .join(Role)
        .where(UserRole.event_id == event_id)
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
        .distinct()
    )
    users = list(users_result.scalars().all())

    for user in users:
        # Determine primary role
        roles = [ur.role.code for ur in user.user_roles if ur.role]
        if RoleCode.STUDENT.value in roles:
            role = "student"
        elif RoleCode.EXPERT.value in roles:
            role = "expert"
        elif RoleCode.BUSINESS.value in roles:
            role = "business"
        elif RoleCode.GUEST.value in roles:
            role = "guest"
        else:
            skipped_count += 1
            continue

        # Get schedule data for this user
        schedule_data = await _get_user_schedule_data(session, user, role, event_id, target_day)
        if not schedule_data:
            skipped_count += 1
            continue

        # Build message
        content = build_eve_reminder(user, role, schedule_data, event)

        # Check for existing notification (dedup)
        existing = await session.execute(
            select(Notification)
            .where(Notification.user_id == user.id)
            .where(Notification.event_id == event_id)
            .where(Notification.type == NotificationType.EVE_OF_DD.value)
            .where(
                or_(
                    Notification.reminder_day == target_day,
                    and_(
                        Notification.reminder_day.is_(None),
                        Notification.scheduled_at.is_not(None),
                        func.date(Notification.scheduled_at) == scheduled_date,
                    ),
                )
            )
            .where(
                Notification.status.notin_(
                    [
                        NotificationStatus.FAILED.value,
                        NotificationStatus.CANCELLED.value,
                        NotificationStatus.BATCHED.value,
                    ]
                )
            )
        )
        if existing.scalars().first():
            skipped_count += 1
            continue

        # Create notification
        notification = Notification(
            event_id=event_id,
            user_id=user.id,
            type=NotificationType.EVE_OF_DD.value,
            content=content,
            status=NotificationStatus.PENDING.value,
            scheduled_at=datetime.now(timezone.utc),
            reminder_day=target_day,
        )
        session.add(notification)
        await session.flush()
        notification_ids.append(notification.id)

        # Create escalation for unreachable users
        if not user.telegram_user_id:
            await create_notification_escalation(session, notification, event_id)
            failed_count += 1
            notification.status = NotificationStatus.FAILED.value
            notification.error_message = "User has no telegram_user_id"

    await session.commit()

    # Send notifications
    if notification_ids:
        # Filter out already-failed ones
        pending_ids = []
        for nid in notification_ids:
            n_result = await session.execute(select(Notification).where(Notification.id == nid))
            n = n_result.scalars().first()
            if n and n.status == NotificationStatus.PENDING.value:
                pending_ids.append(nid)

        if pending_ids:
            s, f = await send_bulk_notifications(session, pending_ids, bot)
            sent_count += s
            failed_count += f

    return ReminderSendResult(
        day=target_day,
        sent=sent_count,
        failed=failed_count,
        skipped=skipped_count,
    )


async def _get_user_schedule_data(
    session: AsyncSession,
    user: User,
    role: str,
    event_id: UUID,
    target_day: date,
) -> dict | None:
    """Get role-specific schedule data for a user."""
    day_start = MSK.localize(datetime.combine(target_day, datetime.min.time()))
    day_end = day_start + timedelta(days=1)

    if role == "student":
        # Find student's project and slot
        # Assuming student is linked to a project via some mechanism
        # For now, return placeholder
        slots_result = await session.execute(
            select(ScheduleSlot)
            .where(ScheduleSlot.event_id == event_id)
            .where(ScheduleSlot.start_time >= day_start)
            .where(ScheduleSlot.start_time < day_end)
            .where(ScheduleSlot.status == SlotStatus.SCHEDULED.value)
            .options(selectinload(ScheduleSlot.room), selectinload(ScheduleSlot.project))
            .limit(1)
        )
        slot = slots_result.scalars().first()
        if slot:
            return {
                "date": target_day,
                "room_name": slot.room.name if slot.room else "...",
                "time": slot.start_time.astimezone(MSK).strftime("%H:%M"),
            }
        return {"date": target_day, "room_name": "...", "time": "..."}

    elif role == "expert":
        # Find expert's room assignment
        from app.models import Expert

        expert_result = await session.execute(select(Expert).where(Expert.user_id == user.id))
        expert = expert_result.scalars().first()

        if not expert:
            return None

        # Get room assignment
        assignment_result = await session.execute(
            select(ExpertRoomAssignment)
            .where(ExpertRoomAssignment.expert_id == expert.id)
            .where(ExpertRoomAssignment.status == "confirmed")
            .options(selectinload(ExpertRoomAssignment.room))
        )
        assignment = assignment_result.scalars().first()

        if not assignment or not assignment.room:
            return None

        # Get projects in the room for this day
        projects_result = await session.execute(
            select(ScheduleSlot)
            .where(ScheduleSlot.room_id == assignment.room_id)
            .where(ScheduleSlot.start_time >= day_start)
            .where(ScheduleSlot.start_time < day_end)
            .where(ScheduleSlot.status == SlotStatus.SCHEDULED.value)
            .options(selectinload(ScheduleSlot.project))
            .order_by(ScheduleSlot.display_order)
        )
        slots = projects_result.scalars().all()

        projects = [s.project.title for s in slots if s.project]
        first_time = slots[0].start_time.astimezone(MSK).strftime("%H:%M") if slots else "..."

        return {
            "date": target_day,
            "room_name": assignment.room.name,
            "time": first_time,
            "projects": projects,
        }

    elif role in ("guest", "business"):
        # For now, return empty program (EPIC-005/006 not implemented)
        return {
            "date": target_day,
            "program": [],
        }

    return None


# ========== Organizer Preview (T013) ==========


async def preview_reminders(
    session: AsyncSession,
    event_id: UUID,
    target_day: date,
) -> ReminderPreview:
    """Preview what eve-of-DD reminders will contain."""
    # Get event
    event_result = await session.execute(select(Event).where(Event.id == event_id))
    event = event_result.scalars().first()
    if not event:
        raise ValueError("Event not found")

    # Calculate scheduled send time (18:00 MSK the day before target_day)
    send_date = target_day - timedelta(days=1)
    scheduled_send_time = MSK.localize(datetime.combine(send_date, datetime.min.time().replace(hour=18, minute=0)))

    # Check if cancellation is still possible (before 17:00 MSK)
    now = datetime.now(MSK)
    cancel_deadline = MSK.localize(datetime.combine(send_date, datetime.min.time().replace(hour=17, minute=0)))
    can_cancel = now < cancel_deadline

    # Count recipients by role
    students = await _count_users_by_role(session, event_id, RoleCode.STUDENT.value)
    experts = await _count_users_by_role(session, event_id, RoleCode.EXPERT.value)
    guests = await _count_users_by_role(session, event_id, RoleCode.GUEST.value)
    business = await _count_users_by_role(session, event_id, RoleCode.BUSINESS.value)

    # Generate sample messages
    sample_messages = SampleMessages(
        student=f"🎓 Завтра {event.name}!\n\nТы выступаешь в Зал 1, время 10:30.\n\nУдачи! 🍀",
        expert=f"👨‍🏫 Завтра {event.name}!\n\nВаша комната: Зал 2\nВремя: 10:30\n\nПроекты:\n• Проект 1\n• Проект 2",
        guest=f"👤 Завтра {event.name}!\n\nИспользуйте /program чтобы получить персональную подборку проектов.",
        business=f"💼 Завтра {event.name}!\n\nИспользуйте /program чтобы получить персональную подборку проектов.",
    )

    # List unreachable participants
    unreachable = await _get_unreachable_participants(session, event_id)

    return ReminderPreview(
        day=target_day,
        scheduled_send_time=scheduled_send_time,
        can_cancel=can_cancel,
        recipients=RecipientCounts(
            students=students,
            experts=experts,
            guests=guests,
            business=business,
            total=students + experts + guests + business,
        ),
        sample_messages=sample_messages,
        unreachable=unreachable,
    )


async def _count_users_by_role(session: AsyncSession, event_id: UUID, role_code: str) -> int:
    """Count users with a specific role for an event."""
    result = await session.execute(
        select(func.count(func.distinct(UserRole.user_id)))
        .join(Role)
        .where(UserRole.event_id == event_id)
        .where(Role.code == role_code)
    )
    return result.scalar() or 0


async def _get_unreachable_participants(
    session: AsyncSession,
    event_id: UUID,
) -> list[UnreachableParticipant]:
    """Get list of participants without telegram_user_id."""
    result = await session.execute(
        select(User)
        .join(UserRole)
        .join(Role)
        .where(UserRole.event_id == event_id)
        .where(or_(User.telegram_user_id.is_(None), User.telegram_user_id == 0))
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
        .distinct()
    )
    users = list(result.scalars().all())

    unreachable = []
    for user in users:
        roles = [ur.role.code for ur in user.user_roles if ur.role]
        role = roles[0] if roles else "unknown"
        user_label = user.full_name or user.username or str(user.id)
        unreachable.append(
            UnreachableParticipant(
                user_id=user.id,
                name=user_label,
                role=role,
                reason="Не запустил бот",
            )
        )

    return unreachable


# ========== Cancel Reminders (T014) ==========


async def cancel_reminders(
    session: AsyncSession,
    event_id: UUID,
    target_day: date,
) -> int:
    """
    Cancel pending eve-of-DD reminders for a specific day.

    Raises CancellationWindowClosedError if after 17:00 MSK.
    """
    # Check cancellation window
    now = datetime.now(MSK)
    cancel_date = target_day - timedelta(days=1)
    cancel_deadline = MSK.localize(datetime.combine(cancel_date, datetime.min.time().replace(hour=17, minute=0)))

    if now >= cancel_deadline:
        raise CancellationWindowClosedError("Отмена рассылки возможна до 17:00")

    # Find and cancel pending notifications
    result = await session.execute(
        update(Notification)
        .where(Notification.event_id == event_id)
        .where(Notification.type == NotificationType.EVE_OF_DD.value)
        .where(
            or_(
                Notification.reminder_day == target_day,
                and_(
                    Notification.reminder_day.is_(None),
                    Notification.scheduled_at.is_not(None),
                    func.date(Notification.scheduled_at) == cancel_date,
                ),
            )
        )
        .where(Notification.status == NotificationStatus.PENDING.value)
        .values(status=NotificationStatus.CANCELLED.value)
        .returning(Notification.id)
    )
    cancelled_ids = result.all()
    await session.commit()

    return len(cancelled_ids)


# ========== Pre-Slot Reminders (T022, T023) ==========


async def check_and_send_pre_slot_reminders(
    session: AsyncSession,
    event_id: UUID,
    bot,
) -> tuple[int, int]:
    """
    Find slots starting in ~1 hour and send reminders.

    Returns (sent, failed).
    """
    now = datetime.now(MSK)
    window_start = now + timedelta(minutes=55)
    window_end = now + timedelta(minutes=65)

    # Find slots in the window
    slots_result = await session.execute(
        select(ScheduleSlot)
        .where(ScheduleSlot.event_id == event_id)
        .where(ScheduleSlot.status == SlotStatus.SCHEDULED.value)
        .where(ScheduleSlot.start_time >= window_start)
        .where(ScheduleSlot.start_time <= window_end)
        .options(
            selectinload(ScheduleSlot.room),
            selectinload(ScheduleSlot.project),
        )
    )
    slots = list(slots_result.scalars().all())

    if not slots:
        return 0, 0

    notification_ids = []

    for slot in slots:
        # Find affected participants
        participants = await _get_slot_participants(session, slot)

        for user, role in participants:
            # Check dedup: skip if notification exists
            existing = await session.execute(
                select(Notification)
                .where(Notification.user_id == user.id)
                .where(Notification.schedule_slot_id == slot.id)
                .where(Notification.type == NotificationType.PRE_SLOT.value)
                .where(Notification.status != NotificationStatus.FAILED.value)
            )
            if existing.scalars().first():
                continue

            # Check 30-min cooldown
            cooldown_threshold = now - timedelta(minutes=30)
            recent = await session.execute(
                select(Notification)
                .where(Notification.user_id == user.id)
                .where(Notification.type == NotificationType.PRE_SLOT.value)
                .where(Notification.status == NotificationStatus.SENT.value)
                .where(Notification.sent_at >= cooldown_threshold)
            )
            if recent.scalars().first():
                continue

            # Build and create notification
            content = build_pre_slot_reminder(
                user,
                role,
                slot,
                room=slot.room,
                project_title=slot.project.title if slot.project else None,
            )

            notification = Notification(
                event_id=event_id,
                user_id=user.id,
                schedule_slot_id=slot.id,
                type=NotificationType.PRE_SLOT.value,
                content=content,
                status=NotificationStatus.PENDING.value,
                scheduled_at=now.astimezone(pytz.UTC),
            )
            session.add(notification)
            await session.flush()
            notification_ids.append(notification.id)

    await session.commit()

    if notification_ids:
        return await send_bulk_notifications(session, notification_ids, bot)

    return 0, 0


async def _get_slot_participants(
    session: AsyncSession,
    slot: ScheduleSlot,
) -> list[tuple[User, str]]:
    """Get users who should receive pre-slot reminder for this slot."""
    participants = []

    # Find students linked to this project via ParticipationRequest
    if slot.project_id:
        from app.models import ParticipationRequest

        student_result = await session.execute(
            select(ParticipationRequest)
            .where(ParticipationRequest.project_id == slot.project_id)
            .where(ParticipationRequest.user_id.isnot(None))
            .options(selectinload(ParticipationRequest.user))
        )
        for pr in student_result.scalars().all():
            if pr.user:
                participants.append((pr.user, "student"))

    # Find experts assigned to this room
    expert_result = await session.execute(
        select(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.room_id == slot.room_id)
        .where(ExpertRoomAssignment.status == "confirmed")
        .options(selectinload(ExpertRoomAssignment.expert))
    )
    for assignment in expert_result.scalars().all():
        if assignment.expert and assignment.expert.user_id:
            user_result = await session.execute(select(User).where(User.id == assignment.expert.user_id))
            user = user_result.scalars().first()
            if user:
                participants.append((user, "expert"))

    # TODO: Find guests/business with this project in their program
    # EPIC-005/006 not implemented

    return participants


# ========== Timing Shift Notifications (T026, T027) ==========


async def queue_timing_shift_notifications(
    session: AsyncSession,
    change_log: ScheduleChangeLog,
    event_id: UUID,
) -> int:
    """
    Queue timing shift notifications for affected participants.

    Returns number of notifications queued.
    """
    slot_result = await session.execute(
        select(ScheduleSlot)
        .where(ScheduleSlot.id == change_log.schedule_slot_id)
        .options(selectinload(ScheduleSlot.project), selectinload(ScheduleSlot.room))
    )
    slot = slot_result.scalars().first()
    if not slot:
        return 0

    # Build notification content
    project_title = slot.project.title if slot.project else "Проект"

    if change_log.change_type == "cancelled":
        content = f"❌ {project_title} отменён."
    elif change_log.change_type == "restored":
        new_time = change_log.new_start_time.astimezone(MSK).strftime("%H:%M") if change_log.new_start_time else "..."
        content = f"✅ {project_title} восстановлен: {new_time}"
    else:
        old_time = change_log.old_start_time.astimezone(MSK).strftime("%H:%M") if change_log.old_start_time else "..."
        new_time = change_log.new_start_time.astimezone(MSK).strftime("%H:%M") if change_log.new_start_time else "..."
        content = f"🔄 {project_title} перенесён: было {old_time} → стало {new_time}"

        if change_log.old_room_id != change_log.new_room_id and change_log.new_room_id:
            room_result = await session.execute(select(Room).where(Room.id == change_log.new_room_id))
            new_room = room_result.scalars().first()
            if new_room:
                content += f", {new_room.name}"

    # Find affected participants
    participants = await _get_slot_participants(session, slot)

    now = datetime.now(timezone.utc)
    batch_scheduled = now + timedelta(minutes=5)
    queued = 0

    for user, role in participants:
        batch_key = f"{user.id}:{event_id}:timing_shift"

        # Check for existing pending notification with same batch_key
        existing = await session.execute(
            select(Notification)
            .where(Notification.batch_key == batch_key)
            .where(Notification.status == NotificationStatus.PENDING.value)
        )
        existing_notif = existing.scalars().first()

        if existing_notif:
            # Mark existing as batched, we'll combine later
            existing_notif.status = NotificationStatus.BATCHED.value
            await session.flush()

        # Create new notification
        notification = Notification(
            event_id=event_id,
            user_id=user.id,
            schedule_slot_id=slot.id,
            type=NotificationType.TIMING_SHIFT.value,
            content=content,
            status=NotificationStatus.PENDING.value,
            scheduled_at=batch_scheduled,
            batch_key=batch_key,
        )
        session.add(notification)
        queued += 1

    # Mark change log as notified
    change_log.notifications_sent = True
    await session.commit()

    return queued


async def process_pending_batches(
    session: AsyncSession,
    bot,
) -> tuple[int, int]:
    """
    Process pending timing shift notifications that are due.

    Batches multiple changes per user into a single message.
    Returns (sent, failed).
    """
    now = datetime.now(timezone.utc)
    sent = 0
    failed = 0

    while True:
        # Find pending timing_shift notifications that are due (paginated)
        result = await session.execute(
            select(Notification)
            .where(Notification.type == NotificationType.TIMING_SHIFT.value)
            .where(Notification.status == NotificationStatus.PENDING.value)
            .where(Notification.scheduled_at <= now)
            .options(selectinload(Notification.user))
            .limit(500)
        )
        notifications = list(result.scalars().all())

        if not notifications:
            break

        # Group by user
        by_user: dict[UUID, list[Notification]] = {}
        for n in notifications:
            if n.user_id not in by_user:
                by_user[n.user_id] = []
            by_user[n.user_id].append(n)

        for user_id, user_notifications in by_user.items():
            # Build batch message
            if len(user_notifications) == 1:
                content = user_notifications[0].content
            else:
                lines = ["📋 Изменения в расписании:\n"]
                for n in user_notifications:
                    lines.append(f"• {n.content}")
                content = "\n".join(lines)

                # Truncate long batch messages
                if len(content) > TELEGRAM_MAX_LENGTH:
                    included_lines = ["📋 Изменения в расписании:\n"]
                    remaining = len(user_notifications)
                    for n in user_notifications:
                        line = f"• {n.content}"
                        test_msg = "\n".join(included_lines + [line])
                        suffix = f"\n\n...и ещё {remaining - 1} изменений"
                        if len(test_msg) + len(suffix) > TELEGRAM_MAX_LENGTH:
                            extra = len(user_notifications) - (len(included_lines) - 1)
                            included_lines.append(f"\n...и ещё {extra} изменений")
                            break
                        included_lines.append(line)
                        remaining -= 1
                    content = "\n".join(included_lines)

            # Get user
            user = user_notifications[0].user
            if not user or not user.telegram_user_id:
                for n in user_notifications:
                    n.status = NotificationStatus.FAILED.value
                    n.error_message = "User has no telegram_user_id"
                failed += 1
                continue

            # Send
            try:
                await bot.send_message(
                    chat_id=user.telegram_user_id,
                    text=content[:TELEGRAM_MAX_LENGTH],
                )
                for n in user_notifications:
                    n.status = NotificationStatus.SENT.value
                    n.sent_at = now
                sent += 1
            except Exception as e:
                for n in user_notifications:
                    n.status = NotificationStatus.FAILED.value
                    n.error_message = str(e)[:500]
                failed += 1

        await session.commit()

    return sent, failed


# ========== Dashboard Queries (T031) ==========


async def get_notification_dashboard(
    session: AsyncSession,
    event_id: UUID,
    type_filter: str | None = None,
    day_filter: date | None = None,
) -> NotificationDashboard:
    """Get notification delivery statistics."""
    # Base query
    query = select(Notification).where(Notification.event_id == event_id)

    if type_filter:
        query = query.where(Notification.type == type_filter)

    if day_filter:
        day_start = MSK.localize(datetime.combine(day_filter, datetime.min.time()))
        day_end = day_start + timedelta(days=1)
        query = query.where(Notification.created_at >= day_start)
        query = query.where(Notification.created_at < day_end)

    result = await session.execute(query.options(selectinload(Notification.user)))
    notifications = list(result.scalars().all())

    # Aggregate by status
    total = len(notifications)
    sent = sum(1 for n in notifications if n.status == NotificationStatus.SENT.value)
    failed = sum(1 for n in notifications if n.status == NotificationStatus.FAILED.value)
    pending = sum(1 for n in notifications if n.status == NotificationStatus.PENDING.value)

    # Aggregate by role
    role_stats: dict[str, dict] = {}
    for n in notifications:
        # Get user role (simplified)
        role = "unknown"
        if n.user:
            user_roles = await session.execute(select(UserRole).join(Role).where(UserRole.user_id == n.user.id))
            for ur in user_roles.scalars().all():
                if ur.role:
                    role = ur.role.code
                    break

        if role not in role_stats:
            role_stats[role] = {"sent": 0, "failed": 0, "pending": 0}

        if n.status == NotificationStatus.SENT.value:
            role_stats[role]["sent"] += 1
        elif n.status == NotificationStatus.FAILED.value:
            role_stats[role]["failed"] += 1
        elif n.status == NotificationStatus.PENDING.value:
            role_stats[role]["pending"] += 1

    # Aggregate by type
    type_stats: dict[str, dict] = {}
    for n in notifications:
        if n.type not in type_stats:
            type_stats[n.type] = {"sent": 0, "failed": 0, "pending": 0}

        if n.status == NotificationStatus.SENT.value:
            type_stats[n.type]["sent"] += 1
        elif n.status == NotificationStatus.FAILED.value:
            type_stats[n.type]["failed"] += 1
        elif n.status == NotificationStatus.PENDING.value:
            type_stats[n.type]["pending"] += 1

    # Get unreachable participants
    unreachable = await _get_unreachable_participants(session, event_id)

    return NotificationDashboard(
        summary=StatusSummary(total=total, sent=sent, failed=failed, pending=pending),
        by_role=[RoleStats(role=role, **stats) for role, stats in role_stats.items()],
        by_type=[TypeStats(type=t, **stats) for t, stats in type_stats.items()],
        unreachable=unreachable,
    )


async def get_notifications(
    session: AsyncSession,
    event_id: UUID,
    user_id: UUID | None = None,
    type_filter: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> NotificationListResponse:
    """List notifications with filters."""
    query = (
        select(Notification)
        .where(Notification.event_id == event_id)
        .options(selectinload(Notification.user))
        .order_by(Notification.created_at.desc())
    )

    if user_id:
        query = query.where(Notification.user_id == user_id)
    if type_filter:
        query = query.where(Notification.type == type_filter)
    if status_filter:
        query = query.where(Notification.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    notifications = list(result.scalars().all())

    items = [
        NotificationItem(
            id=n.id,
            user_name=n.user.full_name if n.user else None,
            type=n.type,
            status=n.status,
            scheduled_at=n.scheduled_at,
            sent_at=n.sent_at,
            error_message=n.error_message,
            retry_count=n.retry_count,
        )
        for n in notifications
    ]

    return NotificationListResponse(total=total, items=items)
