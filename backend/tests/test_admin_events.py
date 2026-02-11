"""Tests for admin event creation endpoint."""

import uuid
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import check_organizer, get_current_user
from app.database import get_session
from app.main import app
from app.models.audit_log import AdminAuditLog
from app.models.base import Base
from app.models.event import Event
from app.models.user import User


@pytest.fixture(scope="module")
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                User.__table__,
                Event.__table__,
                AdminAuditLog.__table__,
            ],
        )
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine):
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_factory() as session:
        # Clean up events and audit logs before each test
        await session.execute(delete(AdminAuditLog))
        await session.execute(delete(Event))
        await session.commit()
        yield session
        await session.rollback()


@pytest.fixture
def mock_user():
    user = User(
        telegram_user_id="event_test_user",
        full_name="Event Admin",
        username="eventadmin",
    )
    user.id = uuid.uuid4()
    return user


@pytest.fixture
async def client(session, mock_user):
    async def override_get_session():
        yield session

    async def override_check_organizer():
        return mock_user

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[check_organizer] = override_check_organizer
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_event_success(client: AsyncClient):
    resp = await client.post(
        "/api/v1/admin/events",
        json={
            "name": "Demo Day 2026",
            "start_date": "2026-03-15",
            "end_date": "2026-03-16",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Demo Day 2026"
    assert data["start_date"] == "2026-03-15"
    assert data["end_date"] == "2026-03-16"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_event_with_description(client: AsyncClient):
    resp = await client.post(
        "/api/v1/admin/events",
        json={
            "name": "Test Event",
            "start_date": "2026-04-01",
            "end_date": "2026-04-02",
            "description": "A test event",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["description"] == "A test event"


@pytest.mark.asyncio
async def test_create_event_conflict(client: AsyncClient, session: AsyncSession):
    event = Event(
        name="Existing",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
    )
    session.add(event)
    await session.commit()

    resp = await client.post(
        "/api/v1/admin/events",
        json={
            "name": "Another",
            "start_date": "2026-05-01",
            "end_date": "2026-05-02",
        },
    )
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_event_invalid_dates(client: AsyncClient):
    resp = await client.post(
        "/api/v1/admin/events",
        json={
            "name": "Bad Dates",
            "start_date": "2026-03-20",
            "end_date": "2026-03-15",
        },
    )
    assert resp.status_code == 422
