from datetime import date

import pytest
from sqlalchemy import select

from app.models.clustering_run import ClusteringRun
from app.models.event import Event
from app.models.project import Project
from app.models.room import Room
from app.models.room_project import RoomProject
from app.services.admin import clustering_service


@pytest.mark.asyncio
async def test_move_project_reassigns_project(session):
    event = Event(name="DemoDay", start_date=date.today(), end_date=date.today())
    session.add(event)
    await session.flush()

    run = ClusteringRun(event_id=event.id, num_rooms=2, status="draft")
    session.add(run)
    await session.flush()

    source_room = Room(
        clustering_run_id=run.id,
        name="Source",
        theme_rationale="Source room",
        display_order=0,
    )
    target_room = Room(
        clustering_run_id=run.id,
        name="Target",
        theme_rationale="Target room",
        display_order=1,
    )
    session.add_all([source_room, target_room])
    await session.flush()

    project = Project(
        event_id=event.id,
        title="Smart Sorting",
        description="Sorting project",
        author="Test Author",
        telegram_contact="@test",
        source="upload",
    )
    session.add(project)
    await session.flush()

    assignment = RoomProject(
        room_id=source_room.id,
        project_id=project.id,
        is_manual=False,
    )
    session.add(assignment)
    await session.flush()

    await clustering_service.move_project(session, run.id, project.id, target_room.id)

    result = await session.execute(
        select(RoomProject).where(RoomProject.project_id == project.id)
    )
    moved = result.scalar_one()
    assert moved.room_id == target_room.id
    assert moved.is_manual is True


@pytest.mark.asyncio
async def test_move_project_rejects_invalid_target(session):
    event = Event(name="DemoDay", start_date=date.today(), end_date=date.today())
    session.add(event)
    await session.flush()

    run = ClusteringRun(event_id=event.id, num_rooms=1, status="draft")
    other_run = ClusteringRun(event_id=event.id, num_rooms=1, status="draft")
    session.add_all([run, other_run])
    await session.flush()

    room_in_run = Room(
        clustering_run_id=run.id,
        name="Run room",
        theme_rationale="Run room",
        display_order=0,
    )
    room_other = Room(
        clustering_run_id=other_run.id,
        name="Other room",
        theme_rationale="Other room",
        display_order=0,
    )
    session.add_all([room_in_run, room_other])
    await session.flush()

    project = Project(
        event_id=event.id,
        title="Safe Move",
        description="Safe move",
        author="Tester",
        telegram_contact="@test",
        source="upload",
    )
    session.add(project)
    await session.flush()

    assignment = RoomProject(
        room_id=room_in_run.id,
        project_id=project.id,
    )
    session.add(assignment)
    await session.flush()

    with pytest.raises(ValueError, match="Целевой зал"):
        await clustering_service.move_project(
            session, run.id, project.id, room_other.id
        )
