"""Tests for admin dashboard, pipeline-status, and coverage endpoints."""

import uuid
from datetime import date, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import check_organizer, get_current_user
from app.database import get_session
from app.main import app
from app.models.base import Base
from app.models.clustering_run import ClusteringRun
from app.models.event import Event
from app.models.expert import Expert
from app.models.expert_briefing import ExpertBriefing
from app.models.expert_room_assignment import ExpertRoomAssignment
from app.models.notification import Notification
from app.models.participation import ParticipationRequest
from app.models.project import Project
from app.models.role import Role, RoleCode
from app.models.room import Room
from app.models.room_project import RoomProject
from app.models.schedule_slot import ScheduleSlot
from app.models.user import User
from app.models.user_role import UserRole
from app.services.admin import dashboard_service

# --- Fixtures ---

_TABLES = [
    Event.__table__,
    User.__table__,
    Role.__table__,
    Project.__table__,
    ClusteringRun.__table__,
    Room.__table__,
    RoomProject.__table__,
    Expert.__table__,
    ScheduleSlot.__table__,
    ExpertRoomAssignment.__table__,
    ParticipationRequest.__table__,
    Notification.__table__,
    ExpertBriefing.__table__,
    UserRole.__table__,
]


@pytest.fixture(scope="module")
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=_TABLES)
    yield eng
    await eng.dispose()


@pytest.fixture
async def db(engine):
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_user():
    user = User(telegram_user_id="dashboard_test", full_name="Test Admin", username="testadmin")
    user.id = uuid.uuid4()
    return user


@pytest.fixture
async def seed_event(db):
    event = Event(
        name="Demo Day 2026",
        start_date=date.today() + timedelta(days=5),
        end_date=date.today() + timedelta(days=6),
    )
    db.add(event)
    await db.flush()
    return event


@pytest.fixture
async def seed_project(db, seed_event):
    project = Project(
        title="AI Agent",
        event_id=seed_event.id,
        description="Test project",
        author="Author1",
        telegram_contact="@author1",
    )
    db.add(project)
    await db.flush()
    return project


@pytest.fixture
async def seed_clustering(db, seed_event):
    run = ClusteringRun(
        event_id=seed_event.id,
        status="approved",
        num_rooms=2,
        approved_at=datetime.now(),
    )
    db.add(run)
    await db.flush()
    return run


@pytest.fixture
async def seed_room(db, seed_clustering):
    room = Room(
        name="Зал 1",
        clustering_run_id=seed_clustering.id,
        theme_rationale="Test theme",
    )
    db.add(room)
    await db.flush()
    return room


# --- Pipeline Status Tests (T009) ---


@pytest.mark.asyncio
async def test_pipeline_status_no_event(db):
    """All steps not_started when no event."""
    result = await dashboard_service.get_pipeline_status(db, event_id=None)

    assert len(result.phases) == 3
    for phase in result.phases:
        assert phase.status == "not_started"
        for step in phase.steps:
            assert step.status == "not_started"

    assert result.next_action is not None
    assert result.next_action.step == "event"


@pytest.mark.asyncio
async def test_pipeline_status_event_only(db, seed_event):
    """Only event step completed, rest not_started."""
    result = await dashboard_service.get_pipeline_status(db, seed_event.id)

    # Event step should be completed
    data_phase = result.phases[0]
    assert data_phase.name == "data"
    assert data_phase.status == "in_progress"
    event_step = data_phase.steps[0]
    assert event_step.name == "event"
    assert event_step.status == "completed"

    # projects step not_started
    assert data_phase.steps[1].status == "not_started"

    # next_action should be projects
    assert result.next_action.step == "projects"


@pytest.mark.asyncio
async def test_pipeline_status_with_data(db, seed_event, seed_project):
    """Event + projects completed."""
    # Add a student user role for students step
    from sqlalchemy import select
    student_role = await db.scalar(select(Role).where(Role.code == RoleCode.STUDENT.value))
    if not student_role:
        student_role = Role(code=RoleCode.STUDENT.value, name="Студент")
        db.add(student_role)
        await db.flush()

    user = User(telegram_user_id="student123", full_name="Student User")
    db.add(user)
    await db.flush()

    user_role = UserRole(
        user_id=user.id,
        role_id=student_role.id,
        event_id=seed_event.id,
    )
    db.add(user_role)
    await db.flush()

    result = await dashboard_service.get_pipeline_status(db, seed_event.id)

    data_phase = result.phases[0]
    assert data_phase.steps[0].status == "completed"  # event
    assert data_phase.steps[1].status == "completed"  # projects
    assert data_phase.steps[2].status == "completed"  # students

    # next_action should be experts
    assert result.next_action.step == "experts"


@pytest.mark.asyncio
async def test_pipeline_status_next_action_none_when_all_complete(
    db, seed_event, seed_project, seed_clustering, seed_room,
):
    """All steps completed → next_action is None."""
    # Add student user role
    from sqlalchemy import select
    student_role = await db.scalar(select(Role).where(Role.code == RoleCode.STUDENT.value))
    if not student_role:
        student_role = Role(code=RoleCode.STUDENT.value, name="Студент")
        db.add(student_role)
        await db.flush()

    student_user = User(telegram_user_id="student456", full_name="Student User")
    db.add(student_user)
    await db.flush()

    user_role = UserRole(
        user_id=student_user.id,
        role_id=student_role.id,
        event_id=seed_event.id,
    )
    db.add(user_role)
    await db.flush()

    # Add expert
    expert = Expert(seed_id="exp1", name="Expert One", event_id=seed_event.id)
    db.add(expert)
    await db.flush()

    # Add expert assignment
    assignment = ExpertRoomAssignment(
        expert_id=expert.id, room_id=seed_room.id, clustering_run_id=seed_clustering.id,
        match_score=0.8, status="confirmed",
    )
    db.add(assignment)
    await db.flush()

    # Mark schedule approved
    seed_clustering.schedule_approved_at = datetime.now()
    await db.flush()

    # Add notification (reminders)
    user = User(telegram_user_id="notif_user", full_name="User")
    db.add(user)
    await db.flush()

    notif = Notification(
        event_id=seed_event.id, user_id=user.id,
        type="eve_of_dd", content="Reminder", status="sent",
    )
    db.add(notif)
    await db.flush()

    # Add briefing
    briefing = ExpertBriefing(
        expert_id=expert.id, event_id=seed_event.id,
        room_id=seed_room.id, project_count=1,
    )
    db.add(briefing)
    await db.flush()

    result = await dashboard_service.get_pipeline_status(db, seed_event.id)

    assert result.next_action is None
    for phase in result.phases:
        assert phase.status == "completed"


# --- Dashboard Stats Tests (T011) ---


@pytest.mark.asyncio
async def test_dashboard_event_summary(db, seed_event):
    """Dashboard includes event summary with days_until."""
    result = await dashboard_service.get_dashboard_stats(db, seed_event.id)

    assert result.event is not None
    assert result.event.name == "Demo Day 2026"
    assert result.event.days_until == 5


@pytest.mark.asyncio
async def test_dashboard_projects_count(db, seed_event, seed_project):
    """Dashboard includes projects count."""
    result = await dashboard_service.get_dashboard_stats(db, seed_event.id)

    assert result.projects.total >= 1


@pytest.mark.asyncio
async def test_dashboard_partners_count(db, seed_event):
    """Dashboard includes partners count with source breakdown."""
    result = await dashboard_service.get_dashboard_stats(db, seed_event.id)

    assert result.partners is not None
    assert result.partners.total >= 0
    assert result.partners.from_bot >= 0
    assert result.partners.from_import >= 0


# --- Coverage 5-level Tests (T013) ---


@pytest.mark.asyncio
async def test_coverage_gap_status(db, seed_event, seed_clustering, seed_room, seed_project):
    """Room with 0 confirmed experts → gap."""
    # Add project to room
    rp = RoomProject(room_id=seed_room.id, project_id=seed_project.id)
    db.add(rp)
    await db.flush()

    result = await dashboard_service.get_coverage_stats(db, seed_event.id)

    assert len(result) >= 1
    room_coverage = next(r for r in result if r.room_id == str(seed_room.id))
    assert room_coverage.coverage_status == "gap"


@pytest.mark.asyncio
async def test_coverage_partial_status(db, seed_event, seed_clustering, seed_room, seed_project):
    """Room with 1 confirmed expert → partial."""
    expert = Expert(seed_id="cov_exp1", name="Expert Partial", event_id=seed_event.id)
    db.add(expert)
    await db.flush()

    assignment = ExpertRoomAssignment(
        expert_id=expert.id, room_id=seed_room.id,
        clustering_run_id=seed_clustering.id, match_score=0.5, status="confirmed",
    )
    db.add(assignment)
    await db.flush()

    result = await dashboard_service.get_coverage_stats(db, seed_event.id)
    room_coverage = next(r for r in result if r.room_id == str(seed_room.id))
    assert room_coverage.coverage_status == "partial"


@pytest.mark.asyncio
async def test_coverage_no_clustering(db, seed_event):
    """No clustering → empty coverage."""
    # Create a separate event without clustering
    event2 = Event(name="Event No Cluster", start_date=date.today(), end_date=date.today())
    db.add(event2)
    await db.flush()

    result = await dashboard_service.get_coverage_stats(db, event2.id)
    assert result == []


# --- Route Tests (T015, T016) ---


@pytest.fixture
async def api_client(db, mock_user):
    """HTTP client with overridden dependencies."""

    async def override_get_session():
        yield db

    async def override_check_organizer():
        return mock_user

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[check_organizer] = override_check_organizer
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test/api/v1",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_pipeline_status_endpoint(api_client):
    """GET /api/v1/admin/pipeline-status returns valid response."""
    response = await api_client.get("/admin/pipeline-status")
    assert response.status_code == 200

    data = response.json()
    assert "phases" in data
    assert len(data["phases"]) == 3
    assert all(p["name"] in ("data", "distribution", "launch") for p in data["phases"])


@pytest.mark.asyncio
async def test_dashboard_endpoint(api_client):
    """GET /api/v1/admin/dashboard returns valid response with new fields."""
    response = await api_client.get("/admin/dashboard")
    assert response.status_code == 200

    data = response.json()
    assert "projects" in data
    assert "partners" in data
    assert "students" in data
    assert "experts" in data


@pytest.mark.asyncio
async def test_coverage_endpoint(api_client):
    """GET /api/v1/admin/coverage returns list."""
    response = await api_client.get("/admin/coverage")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
