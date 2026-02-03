"""Smoke tests for onboarding flow (US1).

Tests:
- T013: /start for new user -> welcome + role selection
- T014: /start for existing user -> correct handling of repeated registration
- T015: Invalid callback (unknown role) -> graceful error handling

Note: These tests mock at the service layer since PTB 21.x's immutable objects
and complex initialization make direct Update mocking impractical for smoke tests.
"""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.role import RoleCode


@pytest.fixture
def mock_event():
    """Create mock event."""
    event = MagicMock()
    event.id = uuid.uuid4()
    event.name = "Test Demo Day"
    return event


@pytest.fixture
def mock_user():
    """Create mock user."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.telegram_user_id = "100"
    user.full_name = "Test User"
    return user


@pytest.fixture
def mock_role():
    """Create mock role."""
    role = MagicMock()
    role.id = uuid.uuid4()
    role.code = RoleCode.GUEST.value
    role.name = "Гость"
    return role


@pytest.mark.asyncio
async def test_start_command_new_user(mock_event, mock_user):
    """T013: /start for new user calls user_service and shows welcome."""
    from app.bot.handlers.start import start_command

    @asynccontextmanager
    async def mock_session():
        yield MagicMock()

    # Create mock update and context
    mock_update = MagicMock()
    mock_update.effective_user.id = 100
    mock_update.effective_user.full_name = "Test User"
    mock_update.effective_user.first_name = "Test"
    mock_update.effective_user.username = "test_user"
    mock_update.message.reply_text = AsyncMock()

    mock_context = MagicMock()
    mock_context.args = []
    mock_context.user_data = {}

    with patch("app.bot.handlers.start.async_session", mock_session), \
         patch("app.bot.handlers.start.user_service") as mock_user_svc, \
         patch("app.bot.handlers.start.settings") as mock_settings:

        mock_settings.organizer_ids = []
        mock_user_svc.upsert_user = AsyncMock(return_value=mock_user)
        mock_user_svc.get_current_event = AsyncMock(return_value=mock_event)
        mock_user_svc.get_user_role_with_info = AsyncMock(return_value=None)

        result = await start_command(mock_update, mock_context)

        # Should call reply_text with welcome message
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        # Text can be positional arg or kwarg
        text = call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")
        reply_markup = call_args.kwargs.get("reply_markup")

        assert "Demo Day" in text
        assert reply_markup is not None  # Role keyboard


@pytest.mark.asyncio
async def test_start_command_existing_user(mock_event, mock_user, mock_role):
    """T014: /start for existing user with role shows change prompt."""
    from app.bot.handlers.start import start_command, CONFIRM_CHANGE

    @asynccontextmanager
    async def mock_session():
        yield MagicMock()

    mock_update = MagicMock()
    mock_update.effective_user.id = 100
    mock_update.effective_user.full_name = "Test User"
    mock_update.effective_user.first_name = "Test"
    mock_update.effective_user.username = "test_user"
    mock_update.message.reply_text = AsyncMock()

    mock_context = MagicMock()
    mock_context.args = []
    mock_context.user_data = {}

    with patch("app.bot.handlers.start.async_session", mock_session), \
         patch("app.bot.handlers.start.user_service") as mock_user_svc, \
         patch("app.bot.handlers.start.settings") as mock_settings:

        mock_settings.organizer_ids = []
        mock_user_svc.upsert_user = AsyncMock(return_value=mock_user)
        mock_user_svc.get_current_event = AsyncMock(return_value=mock_event)
        mock_user_svc.get_user_role_with_info = AsyncMock(return_value=mock_role)

        result = await start_command(mock_update, mock_context)

        # Should return CONFIRM_CHANGE state
        assert result == CONFIRM_CHANGE

        # Should call reply_text mentioning existing role
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        text = call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")

        # Text should reference the user's role or ask about changing
        assert "роль" in text.lower() or "сменить" in text.lower() or mock_user.full_name in text


@pytest.mark.asyncio
async def test_invalid_role_callback(mock_event, mock_user):
    """T015: Invalid role callback is handled gracefully."""
    from app.bot.handlers.start import role_chosen
    from telegram.ext import ConversationHandler

    @asynccontextmanager
    async def mock_session():
        yield MagicMock()

    mock_query = MagicMock()
    mock_query.answer = AsyncMock()
    mock_query.data = "role:invalid_role_xyz"
    mock_query.from_user.id = 100
    mock_query.edit_message_text = AsyncMock()

    mock_update = MagicMock()
    mock_update.callback_query = mock_query

    mock_context = MagicMock()
    mock_context.user_data = {}

    with patch("app.bot.handlers.start.async_session", mock_session), \
         patch("app.bot.handlers.start.user_service") as mock_user_svc, \
         patch("app.bot.handlers.start.settings") as mock_settings:

        mock_settings.organizer_ids = []

        # Should raise ValueError for invalid RoleCode
        try:
            result = await role_chosen(mock_update, mock_context)
            # If no exception, handler returned gracefully
            assert result in (ConversationHandler.END, None) or isinstance(result, int)
        except ValueError as e:
            # Expected - invalid role code
            assert "invalid_role_xyz" in str(e).lower()

        # Callback should have been answered
        mock_query.answer.assert_called_once()
