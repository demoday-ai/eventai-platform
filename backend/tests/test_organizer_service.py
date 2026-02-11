"""Tests for organizer_service."""

from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models.organizer import Organizer
from app.services.admin import organizer_service


@pytest.mark.asyncio
async def test_add_organizer(session):
    org = await organizer_service.add_organizer(
        session,
        telegram_id="org_add_1",
        telegram_username="org_user",
        name="Test Org",
        added_by="admin",
    )

    assert org.id is not None
    assert org.telegram_id == "org_add_1"
    assert org.telegram_username == "org_user"
    assert org.name == "Test Org"
    assert org.added_by == "admin"


@pytest.mark.asyncio
async def test_list_organizers(session):
    await organizer_service.add_organizer(session, telegram_id="org_list_1")
    await organizer_service.add_organizer(session, telegram_id="org_list_2")

    organizers = await organizer_service.list_organizers(session)

    ids = [o.telegram_id for o in organizers]
    assert "org_list_1" in ids
    assert "org_list_2" in ids


@pytest.mark.asyncio
async def test_remove_organizer(session):
    org = await organizer_service.add_organizer(session, telegram_id="org_remove_1")

    deleted = await organizer_service.remove_organizer(session, org.id)
    assert deleted is True

    result = await session.get(Organizer, org.id)
    assert result is None


@pytest.mark.asyncio
async def test_remove_organizer_not_found(session):
    import uuid

    deleted = await organizer_service.remove_organizer(session, uuid.uuid4())
    assert deleted is False


@pytest.mark.asyncio
async def test_is_organizer_db_match(session):
    await organizer_service.add_organizer(session, telegram_id="org_check_1")

    result = await organizer_service.is_organizer(session, "org_check_1")
    assert result is True


@pytest.mark.asyncio
async def test_is_organizer_not_found_falls_back_to_env(session):
    with patch("app.services.admin.organizer_service.settings") as mock_settings:
        mock_settings.is_organizer.return_value = False

        result = await organizer_service.is_organizer(session, "nonexistent_999")

        assert result is False
        mock_settings.is_organizer.assert_called_once_with("nonexistent_999", None)


@pytest.mark.asyncio
async def test_is_organizer_env_fallback_positive(session):
    with patch("app.services.admin.organizer_service.settings") as mock_settings:
        mock_settings.is_organizer.return_value = True

        result = await organizer_service.is_organizer(session, "env_org_1")

        assert result is True


@pytest.mark.asyncio
async def test_is_organizer_passes_username(session):
    with patch("app.services.admin.organizer_service.settings") as mock_settings:
        mock_settings.is_organizer.return_value = False

        await organizer_service.is_organizer(session, "some_id", username="johndoe")

        mock_settings.is_organizer.assert_called_once_with("some_id", "johndoe")


@pytest.mark.asyncio
async def test_seed_from_env_empty_table(session):
    # Clear any existing organizers first
    result = await session.execute(select(Organizer))
    for org in result.scalars().all():
        await session.delete(org)
    await session.flush()

    with patch("app.services.admin.organizer_service.settings") as mock_settings:
        mock_settings.organizer_ids = {"seed_1", "seed_2"}

        count = await organizer_service.seed_from_env(session)

    assert count == 2

    result = await session.execute(select(Organizer))
    orgs = result.scalars().all()
    seeded_ids = {o.telegram_id for o in orgs}
    assert "seed_1" in seeded_ids
    assert "seed_2" in seeded_ids


@pytest.mark.asyncio
async def test_seed_from_env_skips_when_not_empty(session):
    # Add an organizer first
    await organizer_service.add_organizer(session, telegram_id="existing_org_seed")

    with patch("app.services.admin.organizer_service.settings") as mock_settings:
        mock_settings.organizer_ids = {"new_seed_1"}

        count = await organizer_service.seed_from_env(session)

    assert count == 0
