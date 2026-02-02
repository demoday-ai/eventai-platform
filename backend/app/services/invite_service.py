"""Invite, coverage, reminder/escalation service for expert assignments."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.escalation import Escalation
from app.models.expert import Expert
from app.models.expert_room_assignment import ExpertRoomAssignment
from app.models.expert_tag import ExpertTag
from app.models.room import Room
from app.models.room_project import RoomProject
from app.services import matching_service

logger = logging.getLogger(__name__)

# ========== US2: Invite functions ==========


async def get_invite_preview(session: AsyncSession, event_id) -> dict | None:
    """Count experts with/without telegram, generate sample message, build bot link."""
    clustering = await matching_service.get_approved_clustering(session, event_id)
    if not clustering:
        return None

    # Check if any approved/invite_ready assignments exist
    count_result = await session.execute(
        select(func.count(ExpertRoomAssignment.id))
        .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        .where(ExpertRoomAssignment.status.in_(["approved", "invite_ready"]))
    )
    total = count_result.scalar() or 0
    if total == 0:
        return None

    # Count experts with/without telegram
    assignments = await session.execute(
        select(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        .where(ExpertRoomAssignment.status.in_(["approved", "invite_ready"]))
        .options(
            selectinload(ExpertRoomAssignment.expert),
            selectinload(ExpertRoomAssignment.room),
        )
    )
    all_assignments = assignments.scalars().all()

    with_tg = sum(1 for a in all_assignments if a.expert.telegram_username)
    without_tg = sum(1 for a in all_assignments if not a.expert.telegram_username)

    # Build bot link
    bot_username = ""
    if settings.bot_token:
        # Extract bot username from token isn't reliable, use a placeholder
        bot_username = "bot"
    bot_link = f"https://t.me/{bot_username}?start=expert"

    # Sample message
    sample = all_assignments[0] if all_assignments else None
    sample_message = ""
    if sample:
        expert = sample.expert
        room = sample.room
        sample_message = (
            f"Здравствуйте, {expert.name}!\n"
            f"Приглашаем на Demo Day!\n"
            f"Рекомендуемый зал: {room.name if room else '...'}\n"
            f"Перейдите по ссылке для подтверждения."
        )

    return {
        "total_experts": len(all_assignments),
        "with_telegram": with_tg,
        "without_telegram": without_tg,
        "sample_message": sample_message,
        "bot_link": bot_link,
    }


async def confirm_invites(session: AsyncSession, event_id) -> dict:
    """Update all approved assignments -> invite_ready. Return bot link and count."""
    clustering = await matching_service.get_approved_clustering(session, event_id)
    if not clustering:
        return {"invite_ready_count": 0, "bot_link": ""}

    result = await session.execute(
        update(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        .where(ExpertRoomAssignment.status == "approved")
        .values(status="invite_ready", status_changed_at=datetime.now(timezone.utc))
        .returning(ExpertRoomAssignment.id)
    )
    count = len(result.all())
    await session.commit()

    bot_link = "https://t.me/bot?start=expert"
    return {"invite_ready_count": count, "bot_link": bot_link}


async def handle_expert_start(
    session: AsyncSession, event_id, telegram_username: str
) -> dict | None:
    """Find expert by username, mark bot_started, return expert + assignment info."""
    from app.services import expert_service

    expert = await expert_service.get_expert_by_telegram(session, event_id, telegram_username)
    if not expert:
        return None

    # Mark bot_started
    if not expert.bot_started:
        expert.bot_started = True
        expert.bot_started_at = datetime.now(timezone.utc)

    # Find latest assignment
    assignment = None
    if expert.assignments:
        assignment = expert.assignments[0]
        # If invite_ready -> update to invited
        if assignment.status == "invite_ready":
            assignment.status = "invited"
            assignment.invite_viewed_at = datetime.now(timezone.utc)
            assignment.status_changed_at = datetime.now(timezone.utc)

    await session.commit()

    expert_info = {
        "id": str(expert.id),
        "name": expert.name,
        "tags": [et.tag.name for et in expert.tags] if expert.tags else [],
    }

    assignment_info = None
    if assignment and assignment.room:
        # Count projects in room
        project_count_result = await session.execute(
            select(func.count(RoomProject.id))
            .where(RoomProject.room_id == assignment.room_id)
        )
        project_count = project_count_result.scalar() or 0

        assignment_info = {
            "id": str(assignment.id),
            "room_id": str(assignment.room_id),
            "room_name": assignment.room.name,
            "match_score": assignment.match_score,
            "status": assignment.status,
            "project_count": project_count,
        }

    return {"expert": expert_info, "assignment": assignment_info}


async def confirm_attendance(session: AsyncSession, assignment_id) -> None:
    """Set assignment status to confirmed."""
    result = await session.execute(
        select(ExpertRoomAssignment).where(ExpertRoomAssignment.id == assignment_id)
    )
    assignment = result.scalars().first()
    if assignment:
        assignment.status = "confirmed"
        assignment.status_changed_at = datetime.now(timezone.utc)
        await session.commit()


async def decline_attendance(session: AsyncSession, assignment_id) -> None:
    """Set assignment status to declined."""
    result = await session.execute(
        select(ExpertRoomAssignment).where(ExpertRoomAssignment.id == assignment_id)
    )
    assignment = result.scalars().first()
    if assignment:
        assignment.status = "declined"
        assignment.status_changed_at = datetime.now(timezone.utc)
        await session.commit()


async def request_reassignment(
    session: AsyncSession, assignment_id
) -> list[tuple[uuid.UUID, str, int]]:
    """Set status to reassign_requested. Return list of alternative rooms."""
    result = await session.execute(
        select(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.id == assignment_id)
        .options(selectinload(ExpertRoomAssignment.room))
    )
    assignment = result.scalars().first()
    if not assignment:
        return []

    assignment.status = "reassign_requested"
    assignment.status_changed_at = datetime.now(timezone.utc)

    # Get all rooms for the same clustering run (excluding current)
    rooms_result = await session.execute(
        select(Room).where(
            Room.clustering_run_id == assignment.room.clustering_run_id
        )
    )
    all_rooms = rooms_result.scalars().all()

    alternatives = []
    for room in all_rooms:
        if room.id == assignment.room_id:
            continue
        # Count projects
        count_result = await session.execute(
            select(func.count(RoomProject.id))
            .where(RoomProject.room_id == room.id)
        )
        count = count_result.scalar() or 0
        alternatives.append((room.id, room.name, count))

    await session.commit()
    return alternatives


async def reassign_expert(
    session: AsyncSession, assignment_id, new_room_id
) -> None:
    """Update room_id, set is_manual=true, status=confirmed."""
    result = await session.execute(
        select(ExpertRoomAssignment).where(ExpertRoomAssignment.id == assignment_id)
    )
    assignment = result.scalars().first()
    if assignment:
        assignment.room_id = new_room_id
        assignment.is_manual = True
        assignment.status = "confirmed"
        assignment.status_changed_at = datetime.now(timezone.utc)
        await session.commit()


async def get_experts_without_telegram(
    session: AsyncSession, event_id
) -> list[Expert]:
    """List experts without telegram_username."""
    result = await session.execute(
        select(Expert)
        .where(Expert.event_id == event_id)
        .where(Expert.telegram_username.is_(None))
    )
    return list(result.scalars().all())


# ========== US3: Coverage functions ==========


async def get_coverage_dashboard(session: AsyncSession, event_id) -> dict | None:
    """Per-room coverage dashboard with status counts and indicators."""
    clustering = await matching_service.get_approved_clustering(session, event_id)
    if not clustering:
        return None

    # Get all rooms
    rooms_result = await session.execute(
        select(Room).where(Room.clustering_run_id == clustering.id)
        .order_by(Room.display_order)
    )
    rooms = rooms_result.scalars().all()
    if not rooms:
        return None

    rooms_data = []
    total_confirmed = 0
    total_declined = 0
    total_no_response = 0
    total_needed = 0

    for room in rooms:
        # Get assignments for this room
        asgn_result = await session.execute(
            select(ExpertRoomAssignment)
            .where(ExpertRoomAssignment.room_id == room.id)
            .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        )
        room_assignments = asgn_result.scalars().all()

        confirmed = sum(1 for a in room_assignments if a.status == "confirmed")
        declined = sum(1 for a in room_assignments if a.status == "declined")
        no_response = sum(
            1 for a in room_assignments
            if a.status in ("invite_ready", "invited", "approved")
        )
        needed = 2  # minimum 2 experts per room

        if confirmed >= needed:
            coverage_level = "covered"
        elif confirmed >= 1:
            coverage_level = "partial"
        else:
            coverage_level = "uncovered"

        rooms_data.append({
            "room_id": str(room.id),
            "room_name": room.name,
            "confirmed": confirmed,
            "declined": declined,
            "no_response": no_response,
            "needed": needed,
            "total_assigned": len(room_assignments),
            "coverage_level": coverage_level,
        })

        total_confirmed += confirmed
        total_declined += declined
        total_no_response += no_response
        total_needed += needed

    coverage_percent = (total_confirmed / total_needed * 100) if total_needed > 0 else 0

    return {
        "rooms": rooms_data,
        "totals": {
            "confirmed": total_confirmed,
            "declined": total_declined,
            "no_response": total_no_response,
            "total_needed": total_needed,
            "coverage_percent": coverage_percent,
        },
    }


async def get_room_coverage_detail(
    session: AsyncSession, event_id, room_id
) -> dict | None:
    """Detailed expert list for a room with statuses and adjacent suggestions."""
    clustering = await matching_service.get_approved_clustering(session, event_id)
    if not clustering:
        return None

    # Get experts assigned to this room
    asgn_result = await session.execute(
        select(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.room_id == room_id)
        .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        .options(
            selectinload(ExpertRoomAssignment.expert)
            .selectinload(Expert.tags)
            .selectinload(ExpertTag.tag),
        )
    )
    assignments = asgn_result.scalars().all()

    experts = []
    for a in assignments:
        experts.append({
            "expert_id": str(a.expert.id),
            "name": a.expert.name,
            "match_score": a.match_score,
            "status": a.status,
            "bot_started": a.expert.bot_started,
            "tags": [et.tag.name for et in a.expert.tags],
        })

    # Find suggested adjacent experts (not assigned to this room)
    # Get room's project tags
    room_tags = set()
    room_tag_data = await matching_service.get_room_tags(session, clustering.id)
    if room_id in room_tag_data:
        _, room_tags = room_tag_data[room_id]
    else:
        # Try UUID match
        for rid, (_, tags) in room_tag_data.items():
            if str(rid) == str(room_id):
                room_tags = tags
                break

    # Get experts assigned to other rooms who have adjacent tags
    suggested = []
    if room_tags:
        # Get all experts with tags not in this room
        other_result = await session.execute(
            select(ExpertRoomAssignment)
            .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
            .where(ExpertRoomAssignment.room_id != room_id)
            .options(
                selectinload(ExpertRoomAssignment.expert)
                .selectinload(Expert.tags)
                .selectinload(ExpertTag.tag),
            )
        )
        other_assignments = other_result.scalars().all()

        for oa in other_assignments:
            expert_tags = {et.tag.name for et in oa.expert.tags}
            adjacent = expert_tags & room_tags
            if adjacent:
                suggested.append({
                    "expert_id": str(oa.expert.id),
                    "name": oa.expert.name,
                    "adjacent_tags": list(adjacent)[:5],
                    "current_room_id": str(oa.room_id),
                })

        # Sort by number of matching tags, limit to 5
        suggested.sort(key=lambda x: len(x["adjacent_tags"]), reverse=True)
        suggested = suggested[:5]

    return {
        "room_id": str(room_id),
        "experts": experts,
        "suggested_adjacent": suggested,
    }


# ========== US5: Reminder/Escalation functions ==========


async def check_and_send_reminders(session: AsyncSession, event_id, bot) -> int:
    """Find experts with status=invited, invite_viewed_at > 3 days ago, send reminders."""
    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.status == "invited")
        .where(ExpertRoomAssignment.reminder_count < 4)
        .options(
            selectinload(ExpertRoomAssignment.expert),
            selectinload(ExpertRoomAssignment.room),
        )
    )
    assignments = result.scalars().all()

    sent = 0
    for a in assignments:
        if not a.invite_viewed_at:
            continue
        days_since = (now - a.invite_viewed_at).days
        if days_since < 3:
            continue
        if not a.expert.bot_started:
            continue

        # Send reminder via bot
        try:
            # We need the expert's telegram chat_id — but we only have username
            # The bot can only message users who have started the bot
            # We'd need user_id stored somewhere; for now log and create escalation
            logger.info(
                "Reminder needed for expert %s (room %s), %d days since invite viewed",
                a.expert.name, a.room.name if a.room else "?", days_since,
            )
            a.reminder_count += 1
            a.last_reminder_at = now

            # Create escalation record
            escalation = Escalation(
                expert_id=a.expert.id,
                room_id=a.room_id,
                event_id=event_id,
                type="no_response_reminder",
                message=f"Эксперт {a.expert.name} не ответил на приглашение ({days_since} дней)",
            )
            session.add(escalation)
            sent += 1
        except Exception:
            logger.exception("Failed to send reminder to %s", a.expert.name)

    if sent > 0:
        await session.commit()

    return sent


async def check_and_escalate(
    session: AsyncSession, event_id, bot, dd_date: datetime | None = None
) -> int:
    """Check for critical escalations: 5+ days no response, uncovered rooms."""
    now = datetime.now(timezone.utc)
    created = 0

    # 1. Experts not responded after 5 days
    result = await session.execute(
        select(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.status == "invited")
        .options(
            selectinload(ExpertRoomAssignment.expert),
            selectinload(ExpertRoomAssignment.room),
        )
    )
    assignments = result.scalars().all()

    for a in assignments:
        if not a.invite_viewed_at:
            continue
        days_since = (now - a.invite_viewed_at).days

        if days_since >= 5:
            # Check if escalation already exists
            existing = await session.execute(
                select(Escalation)
                .where(Escalation.expert_id == a.expert.id)
                .where(Escalation.type == "no_response_escalation")
                .where(Escalation.resolved == False)
            )
            if existing.scalars().first():
                continue

            escalation = Escalation(
                expert_id=a.expert.id,
                room_id=a.room_id,
                event_id=event_id,
                type="no_response_escalation",
                message=f"Эксперт {a.expert.name} не ответил на приглашение ({days_since} дней)",
            )
            session.add(escalation)
            created += 1

    # 2. Check rooms with 0 confirmed (uncovered)
    clustering = await matching_service.get_approved_clustering(session, event_id)
    if clustering:
        rooms_result = await session.execute(
            select(Room).where(Room.clustering_run_id == clustering.id)
        )
        rooms = rooms_result.scalars().all()

        for room in rooms:
            asgn_result = await session.execute(
                select(func.count(ExpertRoomAssignment.id))
                .where(ExpertRoomAssignment.room_id == room.id)
                .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
                .where(ExpertRoomAssignment.status == "confirmed")
            )
            confirmed = asgn_result.scalar() or 0

            if confirmed == 0:
                esc_type = "room_uncovered"
            elif confirmed == 1:
                esc_type = "room_partially_covered"
            else:
                continue

            # Check if escalation already exists for this room
            existing = await session.execute(
                select(Escalation)
                .where(Escalation.room_id == room.id)
                .where(Escalation.type == esc_type)
                .where(Escalation.resolved == False)
            )
            if existing.scalars().first():
                continue

            # Need an expert_id for the escalation — use first assigned expert
            first_asgn = await session.execute(
                select(ExpertRoomAssignment)
                .where(ExpertRoomAssignment.room_id == room.id)
                .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
                .limit(1)
            )
            first = first_asgn.scalars().first()
            if not first:
                continue

            escalation = Escalation(
                expert_id=first.expert_id,
                room_id=room.id,
                event_id=event_id,
                type=esc_type,
                message=f"Зал '{room.name}': {confirmed} подтверждённых экспертов",
            )
            session.add(escalation)
            created += 1

    if created > 0:
        await session.commit()

    return created


async def resolve_escalation(session: AsyncSession, escalation_id) -> None:
    """Set escalation as resolved."""
    # Handle both string and UUID
    if isinstance(escalation_id, str):
        try:
            escalation_id = uuid.UUID(escalation_id)
        except ValueError:
            return

    result = await session.execute(
        select(Escalation).where(Escalation.id == escalation_id)
    )
    escalation = result.scalars().first()
    if escalation:
        escalation.resolved = True
        escalation.resolved_at = datetime.now(timezone.utc)
        await session.commit()


async def mark_no_show(session: AsyncSession, assignment_id) -> None:
    """Mark a confirmed expert as no-show."""
    result = await session.execute(
        select(ExpertRoomAssignment).where(ExpertRoomAssignment.id == assignment_id)
    )
    assignment = result.scalars().first()
    if assignment and assignment.status == "confirmed":
        assignment.status = "no_show"
        assignment.status_changed_at = datetime.now(timezone.utc)
        await session.commit()


async def get_escalations(
    session: AsyncSession, event_id, resolved: bool = False
) -> list[dict]:
    """List escalations with expert/room info."""
    result = await session.execute(
        select(Escalation)
        .where(Escalation.event_id == event_id)
        .where(Escalation.resolved == resolved)
        .options(
            selectinload(Escalation.expert),
            selectinload(Escalation.room),
        )
        .order_by(Escalation.created_at.desc())
    )
    escalations = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "type": e.type,
            "expert_name": e.expert.name if e.expert else "?",
            "room_name": e.room.name if e.room else "?",
            "message": e.message,
            "resolved": e.resolved,
            "created_at": e.created_at.isoformat() if e.created_at else "",
        }
        for e in escalations
    ]
