import asyncio
import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from telegram import Bot

from app.models.clustering_run import ClusteringRun
from app.models.event import Event
from app.models.participation import ParticipationRequest, ParticipationStatus
from app.models.project import Project
from app.models.room import Room
from app.models.room_project import RoomProject
from app.models.user import User

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def get_approved_clustering_run(
    session: AsyncSession, event_id: uuid.UUID
) -> ClusteringRun | None:
    result = await session.execute(
        select(ClusteringRun)
        .where(
            ClusteringRun.event_id == event_id,
            ClusteringRun.approved_at.isnot(None),
        )
        .order_by(ClusteringRun.approved_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def match_project_to_user(
    session: AsyncSession, project: Project
) -> User | None:
    contact = (project.telegram_contact or "").strip().lstrip("@").lower()
    if not contact:
        return None
    result = await session.execute(
        select(User).where(func.lower(User.username) == contact)
    )
    return result.scalar_one_or_none()


def build_slot_message(project: Project, room: Room, event: Event) -> str:
    date_str = event.start_date.strftime("%d.%m.%Y")
    return (
        f"📋 Расписание Demo Day\n\n"
        f"Проект: {project.title}\n"
        f"Дата: {date_str}\n"
        f"Зал: {room.name}\n\n"
        f"Нажми кнопку, чтобы подтвердить ознакомление."
    )


def build_changed_slot_message(project: Project, room: Room, event: Event) -> str:
    date_str = event.start_date.strftime("%d.%m.%Y")
    return (
        f"⚠️ Расписание изменено\n\n"
        f"Проект: {project.title}\n"
        f"Дата: {date_str}\n"
        f"Зал: {room.name}\n\n"
        f"Нажми кнопку, чтобы подтвердить ознакомление."
    )


# ---------------------------------------------------------------------------
# US1: Broadcast slots
# ---------------------------------------------------------------------------


async def broadcast_slots(
    session: AsyncSession,
    event: Event,
    bot: Bot,
) -> dict:
    from app.bot.keyboards import acknowledge_slot_keyboard

    clustering_run = await get_approved_clustering_run(session, event.id)
    if not clustering_run:
        raise ValueError("Нет утверждённого расписания")

    # Load all room_projects for this clustering run
    result = await session.execute(
        select(RoomProject)
        .join(Room, RoomProject.room_id == Room.id)
        .where(Room.clustering_run_id == clustering_run.id)
        .options(joinedload(RoomProject.project), joinedload(RoomProject.room))
    )
    room_projects = result.unique().scalars().all()

    sent = 0
    skipped = 0
    failed = 0
    unregistered = 0
    unregistered_projects = []

    for rp in room_projects:
        project = rp.project
        room = rp.room

        # Find or create ParticipationRequest
        existing = await session.execute(
            select(ParticipationRequest).where(
                ParticipationRequest.event_id == event.id,
                ParticipationRequest.project_id == project.id,
            )
        )
        pr = existing.scalar_one_or_none()

        if pr and pr.room_project_id == rp.id:
            # Slot unchanged — skip
            if pr.status != ParticipationStatus.PENDING:
                skipped += 1
                continue

        # Match project author to registered user
        user = await match_project_to_user(session, project)
        if not user:
            unregistered += 1
            unregistered_projects.append({
                "project_title": project.title,
                "telegram_contact": project.telegram_contact,
            })
            # Still create PR for tracking
            if not pr:
                pr = ParticipationRequest(
                    event_id=event.id,
                    project_id=project.id,
                    room_project_id=rp.id,
                    user_id=None,
                    status=ParticipationStatus.PENDING,
                )
                session.add(pr)
                await session.flush()
            continue

        is_changed = pr and pr.room_project_id != rp.id and pr.status != ParticipationStatus.PENDING

        if not pr:
            pr = ParticipationRequest(
                event_id=event.id,
                project_id=project.id,
                room_project_id=rp.id,
                user_id=user.id,
                status=ParticipationStatus.PENDING,
            )
            session.add(pr)
            await session.flush()
        elif is_changed:
            # Slot changed — reset status
            pr.room_project_id = rp.id
            pr.user_id = user.id
            pr.status = ParticipationStatus.SENT
            pr.acknowledged_at = None
            pr.reminder_sent_at = None
            await session.flush()

        # Build and send message
        if is_changed:
            text = build_changed_slot_message(project, room, event)
        else:
            text = build_slot_message(project, room, event)

        keyboard = acknowledge_slot_keyboard(str(pr.id))

        try:
            msg = await bot.send_message(
                chat_id=int(user.telegram_user_id),
                text=text,
                reply_markup=keyboard,
            )
            pr.status = ParticipationStatus.SENT
            pr.telegram_message_id = msg.message_id
            sent += 1
        except Exception as e:
            logger.warning("Failed to send to %s: %s", user.telegram_user_id, e)
            failed += 1

        await asyncio.sleep(0.04)  # Rate limiting: ~25 msg/sec

    await session.commit()

    return {
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
        "unregistered": unregistered,
        "unregistered_projects": unregistered_projects,
    }


# ---------------------------------------------------------------------------
# US2: Acknowledge participation
# ---------------------------------------------------------------------------


async def acknowledge_participation(
    session: AsyncSession,
    short_id: str,
    telegram_user_id: str,
) -> tuple[bool, str]:
    """Returns (success, message)."""
    result = await session.execute(
        select(ParticipationRequest).where(
            ParticipationRequest.id.cast(str).like(f"{short_id}%")
        )
    )
    pr = result.scalar_one_or_none()

    if not pr:
        return False, "Запрос не найден"

    # Verify user
    if pr.user_id:
        user = await session.get(User, pr.user_id)
        if user and user.telegram_user_id != telegram_user_id:
            return False, "Это не твой слот"

    if pr.status == ParticipationStatus.ACKNOWLEDGED:
        return True, "Ты уже подтвердил ознакомление"

    pr.status = ParticipationStatus.ACKNOWLEDGED
    pr.acknowledged_at = datetime.now(timezone.utc)
    await session.commit()

    return True, "Отлично! Напоминание придёт за день до выступления"


# ---------------------------------------------------------------------------
# US3: Reminders and escalation
# ---------------------------------------------------------------------------


async def send_reminders(
    session: AsyncSession,
    event: Event,
    bot: Bot,
) -> int:
    """Send reminders to unacknowledged students when DD-5d."""
    from app.bot.keyboards import acknowledge_slot_keyboard

    days_until_dd = (event.start_date - date.today()).days
    if days_until_dd > 5:
        return 0

    result = await session.execute(
        select(ParticipationRequest)
        .where(
            ParticipationRequest.event_id == event.id,
            ParticipationRequest.status == ParticipationStatus.SENT,
            ParticipationRequest.reminder_sent_at.is_(None),
            ParticipationRequest.user_id.isnot(None),
        )
        .options(
            joinedload(ParticipationRequest.project),
            joinedload(ParticipationRequest.user),
            joinedload(ParticipationRequest.room_project).joinedload(RoomProject.room),
        )
    )
    requests = result.unique().scalars().all()

    sent_count = 0
    for pr in requests:
        if not pr.user or not pr.room_project:
            continue
        room = pr.room_project.room
        date_str = event.start_date.strftime("%d.%m.%Y")
        text = (
            f"🔔 Напоминаем: ты выступаешь {date_str}, "
            f"зал «{room.name}».\n\n"
            f"Проект: {pr.project.title}\n\n"
            f"Нажми Ознакомлен."
        )
        keyboard = acknowledge_slot_keyboard(str(pr.id))
        try:
            await bot.send_message(
                chat_id=int(pr.user.telegram_user_id),
                text=text,
                reply_markup=keyboard,
            )
            pr.reminder_sent_at = datetime.now(timezone.utc)
            sent_count += 1
            await asyncio.sleep(0.04)
        except Exception as e:
            logger.warning("Reminder failed for %s: %s", pr.user.telegram_user_id, e)

    await session.commit()
    return sent_count


async def escalate_to_organizers(
    session: AsyncSession,
    event: Event,
    bot: Bot,
    organizer_ids: set[str],
) -> int:
    """Escalate unacknowledged students to organizers when DD-2d."""
    days_until_dd = (event.start_date - date.today()).days
    if days_until_dd > 2:
        return 0

    result = await session.execute(
        select(ParticipationRequest)
        .where(
            ParticipationRequest.event_id == event.id,
            ParticipationRequest.status == ParticipationStatus.SENT,
            ParticipationRequest.escalated_at.is_(None),
        )
        .options(
            joinedload(ParticipationRequest.project),
            joinedload(ParticipationRequest.room_project).joinedload(RoomProject.room),
        )
    )
    requests = result.unique().scalars().all()

    if not requests:
        return 0

    lines = [f"⚠️ {len(requests)} студентов не ознакомились с расписанием:\n"]
    for pr in requests:
        room_name = pr.room_project.room.name if pr.room_project else "?"
        lines.append(f"• {pr.project.title} ({pr.project.telegram_contact}) — {room_name}")

    text = "\n".join(lines)

    sent = 0
    for org_id in organizer_ids:
        try:
            await bot.send_message(chat_id=int(org_id), text=text)
            sent += 1
            await asyncio.sleep(0.04)
        except Exception as e:
            logger.warning("Escalation to organizer %s failed: %s", org_id, e)

    now = datetime.now(timezone.utc)
    for pr in requests:
        pr.escalated_at = now
    await session.commit()

    return len(requests)


# ---------------------------------------------------------------------------
# US4: Dashboard / summary
# ---------------------------------------------------------------------------


async def get_participation_summary(
    session: AsyncSession,
    event_id: uuid.UUID,
    room_id: uuid.UUID | None = None,
) -> dict:
    base_q = select(ParticipationRequest).where(
        ParticipationRequest.event_id == event_id
    )

    if room_id:
        base_q = base_q.join(RoomProject).where(RoomProject.room_id == room_id)

    result = await session.execute(
        base_q.options(
            joinedload(ParticipationRequest.room_project).joinedload(RoomProject.room)
        )
    )
    all_requests = result.unique().scalars().all()

    total = len(all_requests)
    acknowledged = sum(1 for r in all_requests if r.status == ParticipationStatus.ACKNOWLEDGED)
    unregistered = sum(1 for r in all_requests if r.user_id is None)
    pending = total - acknowledged - unregistered

    # By room
    rooms: dict[str, dict] = {}
    for r in all_requests:
        if not r.room_project:
            continue
        room = r.room_project.room
        key = str(room.id)
        if key not in rooms:
            rooms[key] = {
                "room_id": room.id,
                "room_name": room.name,
                "total": 0,
                "acknowledged": 0,
                "pending": 0,
            }
        rooms[key]["total"] += 1
        if r.status == ParticipationStatus.ACKNOWLEDGED:
            rooms[key]["acknowledged"] += 1
        elif r.user_id is not None:
            rooms[key]["pending"] += 1

    return {
        "total": total,
        "acknowledged": acknowledged,
        "pending": pending,
        "unregistered": unregistered,
        "by_room": list(rooms.values()),
    }


async def get_unacknowledged_list(
    session: AsyncSession,
    event_id: uuid.UUID,
    room_id: uuid.UUID | None = None,
) -> list[dict]:
    q = (
        select(ParticipationRequest)
        .where(
            ParticipationRequest.event_id == event_id,
            ParticipationRequest.status == ParticipationStatus.SENT,
        )
        .options(
            joinedload(ParticipationRequest.project),
            joinedload(ParticipationRequest.room_project).joinedload(RoomProject.room),
        )
    )

    if room_id:
        q = q.join(RoomProject).where(RoomProject.room_id == room_id)

    result = await session.execute(q)
    requests = result.unique().scalars().all()

    items = []
    for r in requests:
        room_name = r.room_project.room.name if r.room_project else "N/A"
        items.append({
            "request_id": r.id,
            "project_title": r.project.title,
            "author_name": r.project.author,
            "telegram_contact": r.project.telegram_contact,
            "room_name": room_name,
            "status": r.status.value,
            "sent_at": r.created_at,
            "reminder_sent": r.reminder_sent_at is not None,
            "escalated": r.escalated_at is not None,
        })
    return items


async def build_daily_summary_text(
    session: AsyncSession,
    event_id: uuid.UUID,
) -> str:
    summary = await get_participation_summary(session, event_id)
    lines = [
        f"📊 Сводка ознакомлений\n",
        f"Всего: {summary['total']}",
        f"Ознакомились: {summary['acknowledged']}",
        f"Не ответили: {summary['pending']}",
        f"Неподключённые: {summary['unregistered']}",
        f"\nПо залам:",
    ]
    for r in summary["by_room"]:
        lines.append(f"  {r['room_name']}: {r['acknowledged']}/{r['total']}")
    return "\n".join(lines)


async def send_daily_summary(
    session: AsyncSession,
    event: Event,
    bot: Bot,
    organizer_ids: set[str],
) -> bool:
    text = await build_daily_summary_text(session, event.id)
    for org_id in organizer_ids:
        try:
            await bot.send_message(chat_id=int(org_id), text=text)
        except Exception as e:
            logger.warning("Daily summary to %s failed: %s", org_id, e)
    return True
