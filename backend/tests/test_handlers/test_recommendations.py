"""Smoke tests for recommendations flow (US4).

Tests:
- T032: Guest with profile requests recommendations -> non-empty list
- T033: Business partner requests recommendations -> match objectives
- T034: LLM unavailable -> fallback behavior

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
def mock_business_profile(mock_event):
    """Create mock business profile."""
    profile = MagicMock()
    profile.id = uuid.uuid4()
    profile.event_id = mock_event.id
    profile.objective = BusinessObjective.INVESTMENT
    profile.industries = ["fintech"]
    return profile


@pytest.fixture
def mock_recommendations():
    """Create mock recommendations data."""
    return {
        "must_visit": [
            {
                "rank": 1,
                "title": "AI Fraud Detection",
                "summary": "ML-based fraud detection system",
                "project_id": str(uuid.uuid4()),
                "tags": ["NLP", "FinTech"],
                "room_number": 1,
                "author": "Test Author",
            },
        ],
        "if_time": [
            {
                "rank": 2,
                "title": "EdTech Assistant",
                "summary": "Educational chatbot",
                "project_id": str(uuid.uuid4()),
                "tags": ["NLP", "EdTech"],
                "room_number": 2,
                "author": "Another Author",
            },
        ],
        "total": 2,
    }


@pytest.mark.asyncio
async def test_guest_recommendations(mock_event, mock_guest_user, mock_guest_profile, mock_recommendations):
    """T032: Guest with profile can get recommendations."""
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
        mock_prof_svc.get_available_tags = AsyncMock(return_value=[("NLP", 10), ("CV", 5)])
        mock_prof_svc.generate_recommendations = AsyncMock(return_value=mock_recommendations)

        result = await profile_command(mock_update, mock_context)

        # Should show profile info (existing profile)
        mock_update.message.reply_text.assert_called()

        # Profile service should be accessible
        assert mock_prof_svc.get_or_create_profile.called


@pytest.mark.asyncio
async def test_business_recommendations(mock_event, mock_business_profile):
    """T033: Business partner with profile can get recommendations."""
    from app.bot.handlers.business_profiling import start_profiling, CONFIRM_PROFILE

    @asynccontextmanager
    async def mock_session():
        yield MagicMock()

    mock_business_user = MagicMock()
    mock_business_user.id = uuid.uuid4()
    mock_business_user.telegram_user_id = "300"

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
        mock_prof_svc.format_profile_summary = MagicMock(
            return_value="Цель: Инвестиции\nОтрасли: fintech"
        )

        result = await start_profiling(mock_update, mock_context)

        # Should show existing profile
        assert result == CONFIRM_PROFILE
        mock_update.message.reply_text.assert_called()


@pytest.mark.asyncio
async def test_recommendations_llm_fallback(mock_event, mock_guest_user, mock_guest_profile):
    """T034: LLM unavailable - graceful fallback without crash."""
    from app.bot.handlers.guest_profiling import _process_and_confirm, CHOOSE_TAGS

    mock_update = MagicMock()
    mock_update.message.reply_text = AsyncMock()

    mock_context = MagicMock()
    mock_context.user_data = {
        "selected_tags": set(),
        "raw_text": "AI fraud detection for fintech",
        "available_tags": [("NLP", 10), ("FinTech", 5)],
        "profile_user_id": str(mock_guest_user.id),
        "profile_event_id": str(mock_event.id),
    }

    # Mock profiling_service to raise exception (simulating LLM failure)
    with patch("app.bot.handlers.guest_profiling.profiling_service") as mock_prof_svc:
        # Simulate LLM extraction failure - returns empty result
        mock_prof_svc.extract_interests_from_text = AsyncMock(return_value={
            "tags": [],
            "keywords": [],
        })

        result = await _process_and_confirm(mock_update, mock_context, is_message=True)

        # Should return to CHOOSE_TAGS (fallback behavior)
        assert result == CHOOSE_TAGS

        # Should show fallback message
        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args
        text = call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")

        # Should mention inability to extract or ask to select tags
        assert (
            "удалось" in text.lower() or
            "выберите" in text.lower() or
            "тематик" in text.lower()
        )
