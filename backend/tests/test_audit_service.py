"""Tests for audit_service."""

import pytest

from app.models.user import User
from app.services.admin import audit_service


@pytest.fixture
async def test_user(session):
    user = User(
        telegram_user_id="audit_user_1",
        full_name="Audit Tester",
        username="audit_tester",
    )
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_log_action_creates_entry(session, test_user):
    entry = await audit_service.log_action(
        session, test_user, "upload_projects",
        entity_type="projects", entity_id="proj-1",
        details={"loaded": 10},
    )

    assert entry.id is not None
    assert entry.action == "upload_projects"
    assert entry.user_name == "Audit Tester"
    assert entry.entity_type == "projects"
    assert entry.entity_id == "proj-1"
    assert entry.details == {"loaded": 10}


@pytest.mark.asyncio
async def test_log_action_without_user(session):
    entry = await audit_service.log_action(
        session, None, "system_action",
    )

    assert entry.user_id is None
    assert entry.user_name is None
    assert entry.action == "system_action"


@pytest.mark.asyncio
async def test_get_audit_log_returns_entries(session, test_user):
    await audit_service.log_action(session, test_user, "action_a")
    await audit_service.log_action(session, test_user, "action_b")
    await audit_service.log_action(session, test_user, "action_a")

    entries, total = await audit_service.get_audit_log(session)

    assert total >= 3
    assert len(entries) >= 3


@pytest.mark.asyncio
async def test_get_audit_log_filters_by_action(session, test_user):
    await audit_service.log_action(session, test_user, "filter_test_x")
    await audit_service.log_action(session, test_user, "filter_test_y")
    await audit_service.log_action(session, test_user, "filter_test_x")

    entries, total = await audit_service.get_audit_log(session, action="filter_test_x")

    assert total == 2
    assert all(e.action == "filter_test_x" for e in entries)


@pytest.mark.asyncio
async def test_get_audit_log_pagination(session, test_user):
    for i in range(5):
        await audit_service.log_action(session, test_user, "paginate_test")

    entries, total = await audit_service.get_audit_log(
        session, action="paginate_test", limit=2, offset=0
    )

    assert total == 5
    assert len(entries) == 2


@pytest.mark.asyncio
async def test_get_audit_log_with_details(session, test_user):
    await audit_service.log_action(
        session, test_user, "details_test",
        entity_type="projects", entity_id="p-1",
        details={"loaded": 42, "file_hash": "abc123"},
    )

    entries, total = await audit_service.get_audit_log(session, action="details_test")

    assert total == 1
    assert entries[0].entity_type == "projects"
    assert entries[0].entity_id == "p-1"
    assert entries[0].details["loaded"] == 42
    assert entries[0].details["file_hash"] == "abc123"
