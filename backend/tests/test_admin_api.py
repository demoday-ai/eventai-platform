"""Tests for admin API endpoints (audit-log, organizers CRUD)."""

import uuid
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import check_organizer, get_current_user
from app.database import get_session
from app.main import app
from app.models.audit_log import AdminAuditLog
from app.models.base import Base
from app.models.event import Event
from app.models.organizer import Organizer
from app.models.user import User
from app.services.admin import audit_service

# --- Fixtures ---


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
                Organizer.__table__,
            ],
        )
    yield engine
    await engine.dispose()


@pytest.fixture
async def api_session(api_engine):
    async_session_factory = sessionmaker(
        api_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_user():
    user = User(
        telegram_user_id="admin_api_test",
        full_name="API Admin",
        username="apiadmin",
    )
    user.id = uuid.uuid4()
    return user


@pytest.fixture
async def api_client(api_session, mock_user):
    """HTTP client with overridden dependencies."""

    async def override_get_session():
        yield api_session

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


@pytest.fixture
async def seed_event(api_session):
    """Create a test event for endpoints that need it."""
    event = Event(name="Test Event", start_date=date.today(), end_date=date.today())
    api_session.add(event)
    await api_session.flush()
    return event


# --- Audit Log Endpoint Tests ---


@pytest.mark.asyncio
async def test_get_audit_log_empty(api_client):
    response = await api_client.get("/admin/audit-log")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 0
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_get_audit_log_with_entries(api_client, api_session, mock_user):
    await audit_service.log_action(
        api_session, mock_user, "test_action_api",
        entity_type="test", details={"key": "value"},
    )
    await api_session.flush()

    response = await api_client.get("/admin/audit-log")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    actions = [item["action"] for item in data["items"]]
    assert "test_action_api" in actions


@pytest.mark.asyncio
async def test_get_audit_log_filter_by_action(api_client, api_session, mock_user):
    await audit_service.log_action(api_session, mock_user, "api_filter_a")
    await audit_service.log_action(api_session, mock_user, "api_filter_b")
    await api_session.flush()

    response = await api_client.get("/admin/audit-log", params={"action": "api_filter_a"})

    assert response.status_code == 200
    data = response.json()
    assert all(item["action"] == "api_filter_a" for item in data["items"])


@pytest.mark.asyncio
async def test_get_audit_log_pagination(api_client, api_session, mock_user):
    for _ in range(5):
        await audit_service.log_action(api_session, mock_user, "api_paginate")
    await api_session.flush()

    response = await api_client.get(
        "/admin/audit-log", params={"action": "api_paginate", "limit": 2, "offset": 0}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 5
    assert len(data["items"]) == 2


# --- Organizer CRUD Endpoint Tests ---


@pytest.mark.asyncio
async def test_list_organizers_empty(api_client):
    response = await api_client.get("/admin/organizers")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_add_organizer(api_client):
    response = await api_client.post("/admin/organizers", json={
        "telegram_id": "new_org_api_1",
        "telegram_username": "new_user",
        "name": "New Organizer",
    })

    assert response.status_code == 201
    data = response.json()
    assert data["telegram_id"] == "new_org_api_1"
    assert data["telegram_username"] == "new_user"
    assert data["name"] == "New Organizer"
    assert data["added_by"] == "API Admin"
    assert "id" in data


@pytest.mark.asyncio
async def test_add_and_list_organizer(api_client):
    await api_client.post("/admin/organizers", json={
        "telegram_id": "list_test_org",
        "name": "Listed Org",
    })

    response = await api_client.get("/admin/organizers")

    assert response.status_code == 200
    ids = [o["telegram_id"] for o in response.json()]
    assert "list_test_org" in ids


@pytest.mark.asyncio
async def test_delete_organizer(api_client, api_session):
    # Add first
    resp = await api_client.post("/admin/organizers", json={
        "telegram_id": "delete_org_api",
    })
    org_id = resp.json()["id"]

    # Delete
    del_resp = await api_client.delete(f"/admin/organizers/{org_id}")
    assert del_resp.status_code == 204

    # Verify gone
    list_resp = await api_client.get("/admin/organizers")
    ids = [o["id"] for o in list_resp.json()]
    assert org_id not in ids


@pytest.mark.asyncio
async def test_delete_organizer_not_found(api_client):
    fake_id = str(uuid.uuid4())
    response = await api_client.delete(f"/admin/organizers/{fake_id}")
    assert response.status_code == 404
