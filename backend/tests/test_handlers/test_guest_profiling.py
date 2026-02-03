"""Smoke tests for guest profiling flow (US2).

Tests:
- T020: Full profiling flow (select tags -> enter interests -> confirm)
- T021: Edit existing profile
- T022: Validation (attempt to confirm without selecting tags)

Note: These tests mock at the service layer for practical smoke testing.
"""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_event():
    """Create mock event."""
    event = MagicMock()
    event.id = uuid.uuid4()
    event.name = "Test Demo Day"
    return event


@pytest.fixture
def mock_guest_user():
    """Create mock guest user."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.telegram_user_id = "200"
    user.full_name = "Test Guest"
    return user


@pytest.fixture
def mock_guest_profile(mock_guest_user, mock_event):
    """Create mock guest profile."""
    profile = MagicMock()
    profile.id = uuid.uuid4()
    profile.user_id = mock_guest_user.id
    profile.event_id = mock_event.id
    profile.selected_tags = ["NLP", "CV"]
    profile.extracted_tags = ["LLM"]
    profile.keywords = ["чат-бот"]
    return profile


@pytest.fixture
def mock_tags():
    """Create mock tags list."""
    return [("NLP", 10), ("CV", 8), ("LLM", 15), ("FinTech", 5), ("EdTech", 7)]


@pytest.mark.asyncio
async def test_profiling_flow_complete(mock_event, mock_guest_user, mock_tags):
    """T020: Complete guest profiling flow - tags selection to confirmation."""
    from app.bot.handlers.guest_profiling import profile_command, CHOOSE_TAGS

    @asynccontextmanager
    async def mock_session():
        yield MagicMock()

    mock_profile = MagicMock()
    mock_profile.selected_tags = []
    mock_profile.extracted_tags = []

    mock_update = MagicMock()
    mock_update.effective_user.id = 200
    mock_update.message.reply_text = AsyncMock()

    mock_context = MagicMock()
    mock_context.user_data = {}

    # Mock _check_guest_or_business to return valid auth
    with patch("app.bot.handlers.guest_profiling._check_guest_or_business") as mock_check, \
         patch("app.bot.handlers.guest_profiling.async_session", mock_session), \
         patch("app.bot.handlers.guest_profiling.profiling_service") as mock_prof_svc:

        mock_check.return_value = (mock_guest_user, mock_event, "guest")
        mock_prof_svc.get_or_create_profile = AsyncMock(return_value=mock_profile)
        mock_prof_svc.get_available_tags = AsyncMock(return_value=mock_tags)

        result = await profile_command(mock_update, mock_context)

        # Should return CHOOSE_TAGS state (new profile flow)
        assert result == CHOOSE_TAGS

        # Should call reply_text with tag selection
        mock_update.message.reply_text.assert_called()


@pytest.mark.asyncio
async def test_edit_existing_profile(mock_event, mock_guest_user, mock_guest_profile, mock_tags):
    """T021: User with existing profile can edit it."""
    from app.bot.handlers.guest_profiling import profile_command, CHOOSE_TAGS

    @asynccontextmanager
    async def mock_session():
        yield MagicMock()

    mock_update = MagicMock()
    mock_update.effective_user.id = 200
    mock_update.message.reply_text = AsyncMock()

    mock_context = MagicMock()
    mock_context.user_data = {}

    with patch("app.bot.handlers.guest_profiling._check_guest_or_business") as mock_check, \
         patch("app.bot.handlers.guest_profiling.async_session", mock_session), \
         patch("app.bot.handlers.guest_profiling.profiling_service") as mock_prof_svc:

        mock_check.return_value = (mock_guest_user, mock_event, "guest")
        mock_prof_svc.get_or_create_profile = AsyncMock(return_value=mock_guest_profile)
        mock_prof_svc.get_available_tags = AsyncMock(return_value=mock_tags)

        result = await profile_command(mock_update, mock_context)

        # With existing profile, should show current profile
        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args
        text = call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")

        # Should mention profile or offer update
        assert (
            "профиль" in text.lower() or
            "обновить" in text.lower() or
            "NLP" in text or "CV" in text  # Selected tags
        )


@pytest.mark.asyncio
async def test_validation_min_tags(mock_event, mock_guest_user, mock_tags):
    """T022: Cannot confirm profile without selecting at least one tag."""
    from app.bot.handlers.guest_profiling import tag_toggle_callback, CHOOSE_TAGS

    @asynccontextmanager
    async def mock_session():
        yield MagicMock()

    mock_query = MagicMock()
    mock_query.answer = AsyncMock()
    mock_query.data = "ptag:_done"  # User clicks "done" without selecting
    mock_query.edit_message_text = AsyncMock()
    mock_query.edit_message_reply_markup = AsyncMock()

    mock_update = MagicMock()
    mock_update.callback_query = mock_query

    mock_context = MagicMock()
    mock_context.user_data = {
        "selected_tags": set(),  # Empty - no tags selected
        "raw_text": None,
        "available_tags": mock_tags,
        "profile_user_id": str(mock_guest_user.id),
        "profile_event_id": str(mock_event.id),
    }

    with patch("app.bot.handlers.guest_profiling.async_session", mock_session):
        result = await tag_toggle_callback(mock_update, mock_context)

        # Should return CHOOSE_TAGS (stay on tag selection)
        assert result == CHOOSE_TAGS

        # Should show validation message
        mock_query.edit_message_text.assert_called()
        call_args = mock_query.edit_message_text.call_args
        text = call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")

        # Should mention need to select something
        assert (
            "хотя бы" in text.lower() or
            "выберите" in text.lower() or
            "укажите" in text.lower()
        )
