"""Schedule service - generation, CRUD, and change detection."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID

import pytz
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ChangeType,
    ClusteringRun,
    Event,
    RoomProject,
    ScheduleChangeLog,
    ScheduleSlot,
    SlotStatus,
)
from app.schemas.schedule import (
    BreakTime,
    DaySchedule,
    RoomSchedule,
    RoomSummary,
    RoomTimeOverride,
    ScheduleGenerateResult,
    ScheduleResponse,
    ScheduleSlotResponse,
)

logger = logging.getLogger(__name__)
MSK = pytz.timezone("Europe/Moscow")


async def get_approved_clustering(
    session: AsyncSession, event_id: UUID
) -> ClusteringRun | None:
    """Get the latest approved clustering run for an event."""
    result = await session.execute(
        select(ClusteringRun)
        .where(ClusteringRun.event_id == event_id)
        .where(ClusteringRun.status == "approved")
        .order_by(ClusteringRun.created_at.desc())
        .limit(1)
    )
    return result.scalars().first()


def _parse_hm(hm: str) -> tuple[int, int]:
    """Parse 'HH:MM' string into (hour, minute) tuple."""
    parts = hm.split(":")
    return int(parts[0]), int(parts[1])


def _advance_past_breaks(
    current_time: datetime,
    slot_duration: timedelta,
    break_ranges: list[tuple[datetime, datetime]],
) -> datetime:
    """If the slot overlaps any break, advance current_time past the break end."""
    slot_end = current_time + slot_duration
    for brk_start, brk_end in break_ranges:
        # Slot overlaps break if it starts before break ends and ends after break starts
        if current_time < brk_end and slot_end > brk_start:
            current_time = brk_end
            slot_end = current_time + slot_duration
    return current_time


async def generate_schedule(
    session: AsyncSession,
    event_id: UUID,
    clustering_run_id: UUID | None = None,
    day1_start: datetime | None = None,
    day1_end: datetime | None = None,
    day2_start: datetime | None = None,
    day2_end: datetime | None = None,
    slot_duration_minutes: int = 15,
    room_overrides: list[RoomTimeOverride] | None = None,
    breaks: list[BreakTime] | None = None,
) -> ScheduleGenerateResult:
    """
    Generate schedule slots from approved clustering.

    Each project in room_projects gets a 15-min slot.
    Slots are distributed sequentially within each room.
    Day 1: 10:30-19:30 MSK, Day 2: 14:00-19:30 MSK by default.
    """
    # Get clustering run
    if clustering_run_id:
        result = await session.execute(
            select(ClusteringRun)
            .where(ClusteringRun.id == clustering_run_id)
            .options(selectinload(ClusteringRun.rooms))
        )
        clustering = result.scalars().first()
    else:
        clustering = await get_approved_clustering(session, event_id)
        if clustering:
            # Reload with rooms
            result = await session.execute(
                select(ClusteringRun)
                .where(ClusteringRun.id == clustering.id)
                .options(selectinload(ClusteringRun.rooms))
            )
            clustering = result.scalars().first()

    if not clustering:
        raise ValueError("No approved clustering run found")

    # Check if schedule already exists
    existing = await session.execute(
        select(func.count(ScheduleSlot.id))
        .where(ScheduleSlot.clustering_run_id == clustering.id)
    )
    if (existing.scalar() or 0) > 0:
        raise ValueError("Schedule already exists for this clustering run")

    # Get event for dates
    event_result = await session.execute(
        select(Event).where(Event.id == event_id)
    )
    event = event_result.scalars().first()
    if not event:
        raise ValueError("Event not found")

    # Set default times
    event_start = event.start_date
    event_end = event.end_date or event_start

    if not day1_start:
        day1_start = MSK.localize(datetime.combine(event_start, datetime.min.time().replace(hour=10, minute=30)))
    if not day1_end:
        day1_end = MSK.localize(datetime.combine(event_start, datetime.min.time().replace(hour=19, minute=30)))
    if not day2_start and event_end != event_start:
        day2_start = MSK.localize(datetime.combine(event_end, datetime.min.time().replace(hour=14, minute=0)))
    if not day2_end and event_end != event_start:
        day2_end = MSK.localize(datetime.combine(event_end, datetime.min.time().replace(hour=19, minute=30)))

    # Build per-room override map
    overrides_map: dict[UUID, tuple[tuple[int, int], tuple[int, int]]] = {}
    if room_overrides:
        for ov in room_overrides:
            overrides_map[ov.room_id] = (_parse_hm(ov.start_time), _parse_hm(ov.end_time))

    # Get rooms and their projects
    rooms = clustering.rooms
    room_summaries = []
    total_slots = 0
    slot_duration = timedelta(minutes=slot_duration_minutes)

    for room in sorted(rooms, key=lambda r: r.display_order):
        # Get projects for this room
        rp_result = await session.execute(
            select(RoomProject)
            .where(RoomProject.room_id == room.id)
            .options(selectinload(RoomProject.project))
        )
        room_projects = list(rp_result.scalars().all())

        if not room_projects:
            continue

        # Per-room start/end override
        if room.id in overrides_map:
            start_hm, end_hm = overrides_map[room.id]
            room_day1_start = MSK.localize(datetime.combine(
                event_start, datetime.min.time().replace(hour=start_hm[0], minute=start_hm[1])
            ))
            room_day1_end = MSK.localize(datetime.combine(
                event_start, datetime.min.time().replace(hour=end_hm[0], minute=end_hm[1])
            ))
        else:
            room_day1_start = day1_start
            room_day1_end = day1_end

        # Build break ranges for this day
        break_ranges_day1: list[tuple[datetime, datetime]] = []
        if breaks:
            for brk in breaks:
                bstart_hm = _parse_hm(brk.start_time)
                bend_hm = _parse_hm(brk.end_time)
                brk_start = MSK.localize(datetime.combine(
                    event_start, datetime.min.time().replace(hour=bstart_hm[0], minute=bstart_hm[1])
                ))
                brk_end = MSK.localize(datetime.combine(
                    event_start, datetime.min.time().replace(hour=bend_hm[0], minute=bend_hm[1])
                ))
                break_ranges_day1.append((brk_start, brk_end))

        # Distribute projects across available time
        current_time = room_day1_start
        day1_limit = room_day1_end
        day2_available = day2_start is not None

        first_slot_time = None
        last_slot_time = None
        slot_count = 0
        display_order = 0

        for rp in room_projects:
            # Advance past breaks
            current_time = _advance_past_breaks(current_time, slot_duration, break_ranges_day1)

            # Check if we need to move to day 2
            if current_time + slot_duration > day1_limit:
                if day2_available and current_time < day2_start:
                    current_time = day2_start
                    day1_limit = day2_end
                else:
                    # No more time available
                    logger.warning(
                        "Room %s: not enough time for all projects, skipping %s",
                        room.name, rp.project.title if rp.project else "?"
                    )
                    continue

            # Create slot
            slot = ScheduleSlot(
                event_id=event_id,
                room_id=room.id,
                project_id=rp.project_id,
                clustering_run_id=clustering.id,
                start_time=current_time,
                end_time=current_time + slot_duration,
                display_order=display_order,
                status=SlotStatus.SCHEDULED.value,
            )
            session.add(slot)

            if first_slot_time is None:
                first_slot_time = current_time
            last_slot_time = current_time

            current_time += slot_duration
            display_order += 1
            slot_count += 1
            total_slots += 1

        room_summaries.append(RoomSummary(
            room_id=room.id,
            room_name=room.name,
            slot_count=slot_count,
            first_slot=first_slot_time,
            last_slot=last_slot_time,
        ))

    await session.commit()

    return ScheduleGenerateResult(
        total_slots=total_slots,
        rooms=room_summaries,
    )


async def get_schedule(
    session: AsyncSession,
    event_id: UUID,
    room_id: UUID | None = None,
    day: datetime | None = None,
    status: str | None = None,
) -> ScheduleResponse:
    """Get schedule grouped by day and room."""
    # Get event name
    event_result = await session.execute(
        select(Event).where(Event.id == event_id)
    )
    event = event_result.scalars().first()
    event_name = event.name if event else "Demo Day"

    # Build query
    query = (
        select(ScheduleSlot)
        .where(ScheduleSlot.event_id == event_id)
        .options(
            selectinload(ScheduleSlot.room),
            selectinload(ScheduleSlot.project),
        )
        .order_by(ScheduleSlot.start_time)
    )

    if room_id:
        query = query.where(ScheduleSlot.room_id == room_id)
    if status:
        query = query.where(ScheduleSlot.status == status)
    if day:
        day_start = MSK.localize(datetime.combine(day, datetime.min.time()))
        day_end = day_start + timedelta(days=1)
        query = query.where(ScheduleSlot.start_time >= day_start)
        query = query.where(ScheduleSlot.start_time < day_end)

    result = await session.execute(query)
    slots = list(result.scalars().all())

    # Group by day, then by room
    days_dict: dict[datetime, dict[UUID, list[ScheduleSlot]]] = defaultdict(lambda: defaultdict(list))

    for slot in slots:
        slot_date = slot.start_time.astimezone(MSK).date()
        days_dict[slot_date][slot.room_id].append(slot)

    # Build response
    days = []
    for date in sorted(days_dict.keys()):
        rooms_for_day = []
        for rid in days_dict[date]:
            room_slots = days_dict[date][rid]
            if not room_slots:
                continue
            room = room_slots[0].room
            rooms_for_day.append(RoomSchedule(
                room_id=rid,
                room_name=room.name if room else "Unknown",
                slots=[
                    ScheduleSlotResponse(
                        id=s.id,
                        room_id=s.room_id,
                        room_name=room.name if room else "Unknown",
                        project_id=s.project_id,
                        project_title=s.project.title if s.project else "Unknown",
                        project_author=s.project.author if s.project else None,
                        start_time=s.start_time,
                        end_time=s.end_time,
                        display_order=s.display_order,
                        status=s.status,
                    )
                    for s in sorted(room_slots, key=lambda x: x.display_order)
                ],
            ))
        days.append(DaySchedule(
            date=date,
            rooms=sorted(rooms_for_day, key=lambda r: r.room_name),
        ))

    return ScheduleResponse(event_name=event_name, days=days)


async def update_slot(
    session: AsyncSession,
    slot_id: UUID,
    update_data: dict,
    changed_by_user_id: UUID | None = None,
) -> tuple[ScheduleSlot, ScheduleChangeLog]:
    """
    Update a schedule slot and create a change log entry.

    Returns (updated_slot, change_log).
    """
    result = await session.execute(
        select(ScheduleSlot)
        .where(ScheduleSlot.id == slot_id)
        .options(selectinload(ScheduleSlot.room), selectinload(ScheduleSlot.project))
    )
    slot = result.scalars().first()
    if not slot:
        raise ValueError("Slot not found")

    # Capture old values
    old_start = slot.start_time
    old_end = slot.end_time
    old_room_id = slot.room_id
    old_status = slot.status

    # Determine change type
    change_type = None
    new_start = update_data.get("start_time")
    new_end = update_data.get("end_time")
    new_room_id = update_data.get("room_id")
    new_status = update_data.get("status")

    time_changed = (new_start and new_start != old_start) or (new_end and new_end != old_end)
    room_changed = new_room_id and new_room_id != old_room_id

    if new_status == SlotStatus.CANCELLED.value and old_status != SlotStatus.CANCELLED.value:
        change_type = ChangeType.CANCELLED.value
    elif new_status == SlotStatus.SCHEDULED.value and old_status == SlotStatus.CANCELLED.value:
        change_type = ChangeType.RESTORED.value
    elif time_changed and room_changed:
        change_type = ChangeType.TIME_AND_ROOM_CHANGED.value
    elif time_changed:
        change_type = ChangeType.TIME_CHANGED.value
    elif room_changed:
        change_type = ChangeType.ROOM_CHANGED.value
    else:
        # No meaningful change
        return slot, None

    # Apply updates
    now = datetime.now(pytz.UTC)
    if new_start:
        slot.start_time = new_start
    if new_end:
        slot.end_time = new_end
    if new_room_id:
        slot.room_id = new_room_id
    if new_status:
        slot.status = new_status
        slot.status_changed_at = now
    slot.updated_at = now

    # Create change log
    change_log = ScheduleChangeLog(
        schedule_slot_id=slot.id,
        event_id=slot.event_id,
        changed_by_user_id=changed_by_user_id,
        change_type=change_type,
        old_start_time=old_start if time_changed else None,
        old_end_time=old_end if time_changed else None,
        old_room_id=old_room_id if room_changed else None,
        new_start_time=new_start if time_changed else None,
        new_end_time=new_end if time_changed else None,
        new_room_id=new_room_id if room_changed else None,
        notifications_sent=False,
    )
    session.add(change_log)

    await session.commit()
    await session.refresh(slot)
    await session.refresh(change_log)

    return slot, change_log


async def approve_schedule(
    session: AsyncSession,
    event_id: UUID,
    clustering_run_id: UUID | None = None,
) -> dict:
    """Mark the schedule as approved by setting schedule_approved_at on clustering_run."""
    if clustering_run_id:
        result = await session.execute(
            select(ClusteringRun).where(ClusteringRun.id == clustering_run_id)
        )
        clustering = result.scalars().first()
    else:
        clustering = await get_approved_clustering(session, event_id)

    if not clustering:
        raise ValueError("No clustering run found")

    # Check schedule exists
    slot_count = await session.execute(
        select(func.count(ScheduleSlot.id))
        .where(ScheduleSlot.clustering_run_id == clustering.id)
    )
    total_slots = slot_count.scalar() or 0
    if total_slots == 0:
        raise ValueError("No schedule to approve")

    # Count rooms and days
    room_count = await session.execute(
        select(func.count(func.distinct(ScheduleSlot.room_id)))
        .where(ScheduleSlot.clustering_run_id == clustering.id)
    )
    rooms = room_count.scalar() or 0

    # Count distinct days
    slots_result = await session.execute(
        select(ScheduleSlot.start_time)
        .where(ScheduleSlot.clustering_run_id == clustering.id)
    )
    all_times = slots_result.scalars().all()
    unique_days = len(set(t.astimezone(MSK).date() for t in all_times))

    # Set approval timestamp
    clustering.schedule_approved_at = datetime.now(pytz.UTC)
    await session.commit()

    return {
        "total_slots": total_slots,
        "rooms": rooms,
        "days": unique_days,
    }


async def get_change_log(
    session: AsyncSession,
    event_id: UUID,
    slot_id: UUID | None = None,
    limit: int = 50,
) -> list[ScheduleChangeLog]:
    """Get schedule change logs."""
    query = (
        select(ScheduleChangeLog)
        .where(ScheduleChangeLog.event_id == event_id)
        .options(
            selectinload(ScheduleChangeLog.schedule_slot).selectinload(ScheduleSlot.project),
            selectinload(ScheduleChangeLog.changed_by),
            selectinload(ScheduleChangeLog.old_room),
            selectinload(ScheduleChangeLog.new_room),
        )
        .order_by(ScheduleChangeLog.created_at.desc())
        .limit(limit)
    )

    if slot_id:
        query = query.where(ScheduleChangeLog.schedule_slot_id == slot_id)

    result = await session.execute(query)
    return list(result.scalars().all())


async def is_schedule_approved(session: AsyncSession, event_id: UUID) -> bool:
    """Check if schedule is approved for the event."""
    clustering = await get_approved_clustering(session, event_id)
    if not clustering:
        return False
    return clustering.schedule_approved_at is not None
