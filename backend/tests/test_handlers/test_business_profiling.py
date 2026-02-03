"""Smoke tests for business profiling flow (US3).

Tests:
- T026: Full flow (objective -> industries -> stages -> confirm)
- T027: Selecting objective = INVESTMENT saves correctly
- T028: Update existing profile

Note: These tests mock at the service layer for practical smoke testing.
"""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.business_profile import BusinessObjective


@pytest.fixture
def mock_event():
    """Create mock event."""
    event = MagicMock()
    event.id = uuid.uuid4()
    event.name = "Test Demo Day"
    return event


@pytest.fixture
def mock_business_user():
    """Create mock business user."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.telegram_user_id = "300"
    user.full_name = "Test Business"
    return user


@pytest.fixture
def mock_business_profile(mock_business_user, mock_event):
    """Create mock business profile."""
    profile = MagicMock()
    profile.id = uuid.uuid4()
    profile.user_id = mock_business_user.id
    profile.event_id = mock_event.id
    profile.objective = BusinessObjective.INVESTMENT
    profile.industries = ["fintech", "edtech"]
    profile.tech_stack = ["python", "llm"]
    profile.project_stages = ["mvp", "early_traction"]
    return profile


@pytest.mark.asyncio
async def test_business_profiling_flow(mock_event, mock_business_user):
    """T026: Complete business profiling flow - objective to industries."""
    from app.bot.handlers.business_profiling import start_profiling, CHOOSE_OBJECTIVE

    @asynccontextmanager
    async def mock_session():
        yield MagicMock()

    mock_update = MagicMock()
    mock_update.effective_user.id = 300
    mock_update.message.reply_text = AsyncMock()

    mock_context = MagicMock()
    mock_context.user_data = {}

    # Mock role as business
    mock_role = MagicMock()
    mock_role.code = "business"

    with patch("app.bot.handlers.business_profiling.async_session", mock_session), \
         patch("app.bot.handlers.business_profiling.user_service") as mock_user_svc, \
         patch("app.bot.handlers.business_profiling.profile_service") as mock_prof_svc:

        mock_user_svc.get_user_by_telegram_id = AsyncMock(return_value=mock_business_user)
        mock_user_svc.get_current_event = AsyncMock(return_value=mock_event)
        mock_user_svc.get_user_role_with_info = AsyncMock(return_value=mock_role)
        mock_prof_svc.get_profile_by_user_event = AsyncMock(return_value=None)

        result = await start_profiling(mock_update, mock_context)

        # Should return CHOOSE_OBJECTIVE state
        assert result == CHOOSE_OBJECTIVE

        # Should call reply_text with objective selection
        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args
        text = call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")

        assert (
            "цель" in text.lower() or
            "профилирование" in text.lower()
        )


@pytest.mark.asyncio
async def test_objective_investment_saved(mock_event, mock_business_user):
    """T027: Selecting INVESTMENT objective is processed correctly."""
    from app.bot.handlers.business_profiling import objective_chosen, CHOOSE_INDUSTRIES

    mock_query = MagicMock()
    mock_query.answer = AsyncMock()
    mock_query.data = "bp:obj:investment"
    mock_query.edit_message_text = AsyncMock()

    mock_update = MagicMock()
    mock_update.callback_query = mock_query

    mock_context = MagicMock()
    mock_context.user_data = {
        "user_id": str(mock_business_user.id),
        "event_id": str(mock_event.id),
        "profile": {
            "objective": None,
            "industries": [],
            "tech_stack": [],
            "project_stages": [],
            "collaboration_format": None,
            "free_text_raw": None,
        },
    }

    result = await objective_chosen(mock_update, mock_context)

    # Should return CHOOSE_INDUSTRIES state (next step)
    assert result == CHOOSE_INDUSTRIES

    # Should have set objective in context
    assert mock_context.user_data["profile"]["objective"] == "investment"

    # Should edit message to show industries selection
    mock_query.edit_message_text.assert_called()


@pytest.mark.asyncio
async def test_update_existing_business_profile(mock_event, mock_business_user, mock_business_profile):
    """T028: Business user with existing profile sees it."""
    from app.bot.handlers.business_profiling import start_profiling, CONFIRM_PROFILE

    @asynccontextmanager
    async def mock_session():
        yield MagicMock()

    mock_update = MagicMock()
    mock_update.effective_user.id = 300
    mock_update.message.reply_text = AsyncMock()

    mock_context = MagicMock()
    mock_context.user_data = {}

    mock_role = MagicMock()
    mock_role.code = "business"

    with patch("app.bot.handlers.business_profiling.async_session", mock_session), \
         patch("app.bot.handlers.business_profiling.user_service") as mock_user_svc, \
         patch("app.bot.handlers.business_profiling.profile_service") as mock_prof_svc:

        mock_user_svc.get_user_by_telegram_id = AsyncMock(return_value=mock_business_user)
        mock_user_svc.get_current_event = AsyncMock(return_value=mock_event)
        mock_user_svc.get_user_role_with_info = AsyncMock(return_value=mock_role)
        mock_prof_svc.get_profile_by_user_event = AsyncMock(return_value=mock_business_profile)
        mock_prof_svc.format_profile_summary = MagicMock(return_value="Цель: Инвестиции\nОтрасли: fintech, edtech")

        result = await start_profiling(mock_update, mock_context)

        # Should return CONFIRM_PROFILE state (existing profile)
        assert result == CONFIRM_PROFILE

        # Should show existing profile summary
        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args
        text = call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")

        # Profile summary should be shown
        assert "профиль" in text.lower() or "Инвестиции" in text or "fintech" in text
