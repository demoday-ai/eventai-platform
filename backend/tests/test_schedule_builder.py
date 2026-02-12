"""Tests for the schedule builder — new endpoints and service functions."""

from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest
import pytz
from sqlalchemy import select

from app.models.clustering_run import ClusteringRun
from app.models.event import Event
from app.models.project import Project
from app.models.room import Room
from app.models.room_project import RoomProject
from app.models.schedule_slot import ScheduleSlot, SlotStatus
from app.schemas.schedule import BreakTime, SlotCreateRequest
from app.services.admin import schedule_service

MSK = pytz.timezone("Europe/Moscow")


# --- Helpers ---

async def _create_event(session, start_date=None, end_date=None):
    """Create a test event."""
    start = start_date or date(2026, 1, 22)
    end = end_date or date(2026, 1, 23)
    event = Event(name="DemoDay Test", start_date=start, end_date=end)
    session.add(event)
    await session.flush()
    return event


async def _create_clustering(session, event_id, status="approved", num_rooms=2):
    """Create an approved clustering run."""
    run = ClusteringRun(event_id=event_id, num_rooms=num_rooms, status=status)
    session.add(run)
    await session.flush()
    return run


async def _create_room(session, clustering_run_id, name="Room 1", order=0, slot_duration_minutes=15):
    """Create a room with optional slot duration."""
    room = Room(
        clustering_run_id=clustering_run_id,
        name=name,
        theme_rationale=f"{name} rationale",
        display_order=order,
        slot_duration_minutes=slot_duration_minutes,
    )
    session.add(room)
    await session.flush()
    return room


async def _create_project(session, event_id, title="Project", author="Author"):
    """Create a project."""
    project = Project(
        event_id=event_id,
        title=title,
        description=f"{title} description",
        author=author,
        telegram_contact="@test",
        source="upload",
    )
    session.add(project)
    await session.flush()
    return project


async def _assign_project(session, room_id, project_id):
    """Assign a project to a room."""
    rp = RoomProject(room_id=room_id, project_id=project_id, is_manual=False)
    session.add(rp)
    await session.flush()
    return rp


# --- Tests: create_slot ---


@pytest.mark.asyncio
async def test_create_project_slot(session):
    """POST /schedule/slots with project_id creates a project slot."""
    event = await _create_event(session)
    run = await _create_clustering(session, event.id)
    room = await _create_room(session, run.id, name="Slot Room")
    project = await _create_project(session, event.id, title="Slot Project")

    data = SlotCreateRequest(
        room_id=room.id,
        start_time=datetime(2026, 1, 22, 10, 30, tzinfo=pytz.UTC),
        end_time=datetime(2026, 1, 22, 10, 45, tzinfo=pytz.UTC),
        slot_type="project",
        project_id=project.id,
    )
    slot = await schedule_service.create_slot(session, event.id, data)

    assert slot.slot_type == "project"
    assert slot.project_id == project.id
    assert slot.room_id == room.id
    assert slot.status == SlotStatus.SCHEDULED.value


@pytest.mark.asyncio
async def test_create_break_slot(session):
    """POST /schedule/slots with slot_type=break creates without project_id."""
    event = await _create_event(session)
    run = await _create_clustering(session, event.id)
    room = await _create_room(session, run.id, name="Break Room")

    data = SlotCreateRequest(
        room_id=room.id,
        start_time=datetime(2026, 1, 22, 12, 30, tzinfo=pytz.UTC),
        end_time=datetime(2026, 1, 22, 13, 0, tzinfo=pytz.UTC),
        slot_type="break",
        title="Обед",
    )
    slot = await schedule_service.create_slot(session, event.id, data)

    assert slot.slot_type == "break"
    assert slot.project_id is None
    assert slot.title == "Обед"


@pytest.mark.asyncio
async def test_create_ceremony_slot(session):
    """POST /schedule/slots with slot_type=ceremony."""
    event = await _create_event(session)
    run = await _create_clustering(session, event.id)
    room = await _create_room(session, run.id, name="Ceremony Room")

    data = SlotCreateRequest(
        room_id=room.id,
        start_time=datetime(2026, 1, 22, 10, 0, tzinfo=pytz.UTC),
        end_time=datetime(2026, 1, 22, 10, 30, tzinfo=pytz.UTC),
        slot_type="ceremony",
        title="Приветствие",
        description="Вступительное слово организаторов",
    )
    slot = await schedule_service.create_slot(session, event.id, data)

    assert slot.slot_type == "ceremony"
    assert slot.project_id is None
    assert slot.title == "Приветствие"
    assert slot.description == "Вступительное слово организаторов"


# --- Tests: delete_slot ---


@pytest.mark.asyncio
async def test_delete_slot(session):
    """DELETE /schedule/slots/{id} removes the slot."""
    event = await _create_event(session)
    run = await _create_clustering(session, event.id)
    room = await _create_room(session, run.id, name="Del Room")

    data = SlotCreateRequest(
        room_id=room.id,
        start_time=datetime(2026, 1, 22, 11, 0, tzinfo=pytz.UTC),
        end_time=datetime(2026, 1, 22, 11, 15, tzinfo=pytz.UTC),
        slot_type="break",
        title="Delete me",
    )
    slot = await schedule_service.create_slot(session, event.id, data)
    slot_id = slot.id

    await schedule_service.delete_slot(session, slot_id)

    result = await session.execute(select(ScheduleSlot).where(ScheduleSlot.id == slot_id))
    assert result.scalars().first() is None


@pytest.mark.asyncio
async def test_delete_slot_not_found(session):
    """DELETE with nonexistent ID raises ValueError."""
    import uuid
    with pytest.raises(ValueError, match="Slot not found"):
        await schedule_service.delete_slot(session, uuid.uuid4())


# --- Tests: get_unplaced_projects ---


@pytest.mark.asyncio
async def test_get_unplaced_projects(session):
    """GET /schedule/unplaced returns projects without active slots."""
    event = await _create_event(session)
    run = await _create_clustering(session, event.id)
    room = await _create_room(session, run.id, name="Unplaced Room")

    p1 = await _create_project(session, event.id, title="Placed Project")
    p2 = await _create_project(session, event.id, title="Unplaced Project")

    await _assign_project(session, room.id, p1.id)
    await _assign_project(session, room.id, p2.id)

    # Create a slot only for p1
    slot = ScheduleSlot(
        event_id=event.id,
        room_id=room.id,
        project_id=p1.id,
        clustering_run_id=run.id,
        start_time=datetime(2026, 1, 22, 10, 30, tzinfo=pytz.UTC),
        end_time=datetime(2026, 1, 22, 10, 45, tzinfo=pytz.UTC),
        display_order=0,
        status=SlotStatus.SCHEDULED.value,
        slot_type="project",
    )
    session.add(slot)
    await session.flush()

    items = await schedule_service.get_unplaced_projects(session, event.id)

    unplaced_ids = {item["id"] for item in items}
    assert p2.id in unplaced_ids
    assert p1.id not in unplaced_ids


# --- Tests: bulk_move_slots ---


@pytest.mark.asyncio
async def test_bulk_move_slots(session):
    """POST /schedule/slots/bulk-move shifts slots after given time."""
    event = await _create_event(session)
    run = await _create_clustering(session, event.id)
    room = await _create_room(session, run.id, name="Bulk Room")

    base_time = datetime(2026, 1, 22, 10, 30, tzinfo=pytz.UTC)

    # Create 3 slots at 10:30, 10:45, 11:00
    for i in range(3):
        slot = ScheduleSlot(
            event_id=event.id,
            room_id=room.id,
            clustering_run_id=run.id,
            start_time=base_time + timedelta(minutes=15 * i),
            end_time=base_time + timedelta(minutes=15 * (i + 1)),
            display_order=i,
            status=SlotStatus.SCHEDULED.value,
            slot_type="project",
        )
        session.add(slot)
    await session.flush()

    # Shift slots at or after 10:45 by +30 minutes
    after_time = base_time + timedelta(minutes=15)
    moved = await schedule_service.bulk_move_slots(session, room.id, after_time, 30)

    assert moved == 2  # 10:45 and 11:00 slots

    # Verify the shifted slots
    result = await session.execute(
        select(ScheduleSlot)
        .where(ScheduleSlot.room_id == room.id)
        .order_by(ScheduleSlot.start_time)
    )
    slots = list(result.scalars().all())

    # SQLite strips timezone, so compare naive datetimes
    def naive(dt):
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    # First slot stays at 10:30
    assert naive(slots[0].start_time) == naive(base_time)
    # Second slot moved from 10:45 to 11:15
    assert naive(slots[1].start_time) == naive(base_time + timedelta(minutes=45))
    # Third slot moved from 11:00 to 11:30
    assert naive(slots[2].start_time) == naive(base_time + timedelta(minutes=60))


# --- Tests: generate_schedule ---


@pytest.mark.asyncio
async def test_generate_returns_unplaced(session):
    """generate_schedule returns unplaced_count when projects don't fit."""
    event = await _create_event(session, start_date=date(2026, 2, 1), end_date=date(2026, 2, 1))
    run = await _create_clustering(session, event.id)
    room = await _create_room(session, run.id, name="Tight Room", slot_duration_minutes=15)

    # Create more projects than fit in 1 hour (4 slots max in 10:30-11:30)
    for i in range(6):
        p = await _create_project(session, event.id, title=f"Gen Unplaced {i}")
        await _assign_project(session, room.id, p.id)

    day_start = MSK.localize(datetime(2026, 2, 1, 10, 30))
    day_end = MSK.localize(datetime(2026, 2, 1, 11, 30))

    result = await schedule_service.generate_schedule(
        session,
        event.id,
        clustering_run_id=run.id,
        day1_start=day_start,
        day1_end=day_end,
        slot_duration_minutes=15,
        force=True,
    )

    assert result.total_slots == 4
    assert result.unplaced_count == 2


@pytest.mark.asyncio
async def test_generate_per_room_duration(session):
    """generate_schedule respects per-room slot_duration_minutes."""
    event = await _create_event(session, start_date=date(2026, 2, 2), end_date=date(2026, 2, 2))
    run = await _create_clustering(session, event.id)

    # Room with 30-min slots
    room30 = await _create_room(session, run.id, name="Room 30min", order=0, slot_duration_minutes=30)
    p1 = await _create_project(session, event.id, title="Long Project")
    await _assign_project(session, room30.id, p1.id)

    day_start = MSK.localize(datetime(2026, 2, 2, 10, 0))
    day_end = MSK.localize(datetime(2026, 2, 2, 19, 30))

    result = await schedule_service.generate_schedule(
        session,
        event.id,
        clustering_run_id=run.id,
        day1_start=day_start,
        day1_end=day_end,
        slot_duration_minutes=15,  # global default is 15
        force=True,
    )

    # The slot should be 30 minutes (per-room), not 15
    slots_result = await session.execute(
        select(ScheduleSlot).where(
            ScheduleSlot.clustering_run_id == run.id,
            ScheduleSlot.project_id == p1.id,
        )
    )
    slot = slots_result.scalars().first()
    assert slot is not None
    duration = (slot.end_time - slot.start_time).total_seconds() / 60
    assert duration == 30


@pytest.mark.asyncio
async def test_break_ranges_day2_fix(session):
    """Break ranges should apply correctly to Day 2 dates."""
    event = await _create_event(session, start_date=date(2026, 2, 3), end_date=date(2026, 2, 4))
    run = await _create_clustering(session, event.id)
    room = await _create_room(session, run.id, name="Break Day2 Room", slot_duration_minutes=15)

    # Create many projects to fill Day 1 and spill into Day 2
    for i in range(50):
        p = await _create_project(session, event.id, title=f"BreakD2 Project {i}")
        await _assign_project(session, room.id, p.id)

    breaks = [BreakTime(start_time="12:30", end_time="13:00")]

    day1_start = MSK.localize(datetime(2026, 2, 3, 10, 30))
    day1_end = MSK.localize(datetime(2026, 2, 3, 19, 30))
    day2_start = MSK.localize(datetime(2026, 2, 4, 14, 0))
    day2_end = MSK.localize(datetime(2026, 2, 4, 19, 30))

    result = await schedule_service.generate_schedule(
        session,
        event.id,
        clustering_run_id=run.id,
        day1_start=day1_start,
        day1_end=day1_end,
        day2_start=day2_start,
        day2_end=day2_end,
        slot_duration_minutes=15,
        breaks=breaks,
        force=True,
    )

    # Should have scheduled some slots on both days
    assert result.total_slots > 0

    # Verify no slot overlaps with break on Day 1 (12:30-13:00)
    slots_result = await session.execute(
        select(ScheduleSlot).where(ScheduleSlot.clustering_run_id == run.id)
    )
    slots = list(slots_result.scalars().all())
    # Use naive datetimes for comparison (SQLite strips tz)
    break_start_d1 = datetime(2026, 2, 3, 12, 30)
    break_end_d1 = datetime(2026, 2, 3, 13, 0)

    for s in slots:
        st = s.start_time.replace(tzinfo=None) if s.start_time.tzinfo else s.start_time
        et = s.end_time.replace(tzinfo=None) if s.end_time.tzinfo else s.end_time
        # Slot should not overlap with break on Day 1
        if st.date() == date(2026, 2, 3):
            overlaps = st < break_end_d1 and et > break_start_d1
            assert not overlaps, f"Slot {st}-{et} overlaps Day 1 break"


# --- Tests: configure_from_text ---


@pytest.mark.asyncio
async def test_configure_from_text_llm_mock(session):
    """configure_from_text parses LLM response into time-frame config (rooms already exist)."""
    event = await _create_event(session, start_date=date(2026, 2, 5), end_date=date(2026, 2, 5))
    run = await _create_clustering(session, event.id)
    # Create 2 rooms in clustering (they already exist from clustering step)
    room1 = Room(clustering_run_id=run.id, name="EdTech", theme_rationale="Education", display_order=0)
    room2 = Room(clustering_run_id=run.id, name="FinTech", theme_rationale="Finance", display_order=1)
    session.add_all([room1, room2])
    await session.flush()

    mock_response = {
        "days": [
            {
                "date_hint": "первый день",
                "start_time": "10:00",
                "end_time": "19:30",
                "slot_duration_minutes": 15,
                "format": "presentation_15min",
                "track_filter": "all_except_research",
                "breaks": [
                    {"start_time": "12:30", "end_time": "13:00", "label": "Обед"}
                ],
                "ceremonies": [
                    {"start_time": "10:00", "end_time": "10:30", "label": "Приветствие"}
                ],
            }
        ]
    }

    with patch("app.services.core.llm_client.send_chat_completion") as mock_llm:
        mock_llm.return_value = mock_response
        result = await schedule_service.configure_from_text(
            session, event.id, "Начинаем в 10, приветствие 30 мин, обед 12:30-13:00. Все кроме научного."
        )

    assert result.rooms_count == 2  # existing rooms from clustering
    assert len(result.parsed_config) == 1
    day = result.parsed_config[0]
    assert day.date_hint == "первый день"
    assert day.start_time == "10:00"
    assert day.end_time == "19:30"
    assert day.slot_duration_minutes == 15
    assert day.track_filter == "all_except_research"
    assert len(day.breaks) == 1
    assert day.breaks[0].label == "Обед"
    assert len(day.ceremonies) == 1
    assert day.ceremonies[0].label == "Приветствие"
    mock_llm.assert_called_once()
