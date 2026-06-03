"""Tests for single-expert deletion endpoint (DELETE /experts/{id})."""

import uuid
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_current_user
from app.database import get_session
from app.main import app
from app.models.audit_log import AdminAuditLog
from app.models.base import Base
from app.models.clustering_run import ClusteringRun
from app.models.event import Event
from app.models.expert import Expert
from app.models.expert_room_assignment import ExpertRoomAssignment
from app.models.expert_tag import ExpertTag
from app.models.room import Room
from app.models.tag import Tag
from app.models.user import User


@pytest.fixture(scope="module")
async def api_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                User.__table__,
                Event.__table__,
                AdminAuditLog.__table__,
                Tag.__table__,
                ClusteringRun.__table__,
                Room.__table__,
                Expert.__table__,
                ExpertTag.__table__,
                ExpertRoomAssignment.__table__,
            ],
        )
    yield engine
    await engine.dispose()


@pytest.fixture
async def api_session(api_engine):
    factory = sessionmaker(api_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_user():
    user = User(telegram_user_id="del_expert_test", full_name="Admin", username="admin")
    user.id = uuid.uuid4()
    return user


@pytest.fixture
async def api_client(api_session, mock_user):
    async def override_get_session():
        yield api_session

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def seed_event(api_session):
    event = Event(name="Test Event", start_date=date.today(), end_date=date.today())
    api_session.add(event)
    await api_session.flush()
    return event


@pytest.mark.asyncio
async def test_delete_expert_removes_row(api_client, api_session, seed_event):
    expert = Expert(seed_id="e1", name="Иван Эксперт", event_id=seed_event.id)
    api_session.add(expert)
    await api_session.flush()
    expert_id = str(expert.id)

    resp = await api_client.delete(f"/experts/{expert_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] == expert_id

    remaining = await api_session.scalar(select(Expert).where(Expert.id == expert.id))
    assert remaining is None


@pytest.mark.asyncio
async def test_delete_expert_not_found(api_client, seed_event):
    fake_id = str(uuid.uuid4())
    resp = await api_client.delete(f"/experts/{fake_id}")
    assert resp.status_code == 404
