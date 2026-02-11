from datetime import date
from unittest.mock import patch

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

    result = await session.execute(select(RoomProject).where(RoomProject.project_id == project.id))
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
        await clustering_service.move_project(session, run.id, project.id, room_other.id)


@pytest.mark.asyncio
async def test_suggest_room_themes_returns_themes(session):
    """Test suggest_room_themes returns N themes."""
    event = Event(name="DemoDay", start_date=date.today(), end_date=date.today())
    session.add(event)
    await session.flush()

    # Add 10 projects
    for i in range(10):
        project = Project(
            event_id=event.id,
            title=f"Project {i}",
            description=f"NLP project about {i}",
            author=f"Author {i}",
            telegram_contact=f"@user{i}",
            source="upload",
        )
        session.add(project)
    await session.flush()

    # Mock LLM
    with patch("app.services.admin.clustering_service.llm_client.send_chat_completion") as mock_llm:
        mock_llm.return_value = {"themes": ["NLP и языковые модели", "AI в образовании", "Computer Vision"]}

        themes = await clustering_service.suggest_room_themes(session, event.id, num_rooms=3)

        assert len(themes) == 3
        assert themes[0] == "NLP и языковые модели"
        mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_suggest_room_themes_fallback_on_error(session):
    """Test suggest_room_themes returns generic themes on LLM failure."""
    event = Event(name="DemoDay", start_date=date.today(), end_date=date.today())
    session.add(event)
    await session.flush()

    # Add 2 projects (minimum required)
    for i in range(2):
        project = Project(
            event_id=event.id,
            title=f"Project {i}",
            description=f"Description {i}",
            author=f"Author {i}",
            telegram_contact=f"@user{i}",
            source="upload",
        )
        session.add(project)
    await session.flush()

    # Mock LLM to return invalid response
    with patch("app.services.admin.clustering_service.llm_client.send_chat_completion") as mock_llm:
        mock_llm.return_value = {"themes": []}  # invalid

        themes = await clustering_service.suggest_room_themes(session, event.id, num_rooms=3)

        # Should fallback to generic themes
        assert len(themes) == 3
        assert themes == ["Зал 1", "Зал 2", "Зал 3"]
