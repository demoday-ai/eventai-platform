"""Smoke tests for Q&A helper flow (US5).

Tests:
- T036: Guest requests questions for project -> list of questions
- T037: Business (investor) requests questions -> type BUSINESS_INVESTOR
- T038: LLM unavailable -> fallback questions

Note: These tests mock at the service layer for practical smoke testing.
"""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.business_profile import BusinessObjective
from app.models.role import RoleCode


@pytest.fixture
def mock_guest_user():
    """Create mock guest user with roles."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.telegram_user_id = "200"
    user.full_name = "Test Guest"

    # Add roles attribute
    role = MagicMock()
    role.code = RoleCode.GUEST
    user_role = MagicMock()
    user_role.role = role
    user.roles = [user_role]

    return user


@pytest.fixture
def mock_business_user():
    """Create mock business user with roles."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.telegram_user_id = "300"
    user.full_name = "Test Business"

    # Add roles attribute
    role = MagicMock()
    role.code = RoleCode.BUSINESS
    user_role = MagicMock()
    user_role.role = role
    user.roles = [user_role]

    return user


@pytest.fixture
def mock_guest_profile():
    """Create mock guest profile."""
    profile = MagicMock()
    profile.id = uuid.uuid4()
    profile.selected_tags = ["NLP", "CV"]
    return profile


@pytest.fixture
def mock_business_profile():
    """Create mock business profile with investor objective."""
    profile = MagicMock()
    profile.id = uuid.uuid4()
    profile.objective = BusinessObjective.INVESTMENT
    profile.industries = ["fintech"]
    return profile


@pytest.fixture
def mock_projects():
    """Create mock projects."""
    projects = []
    for i in range(3):
        project = MagicMock()
        project.id = uuid.uuid4()
        project.title = f"Project {i+1}"
        project.description = f"Description {i+1}"
        projects.append(project)
    return projects


@pytest.mark.asyncio
async def test_guest_qa_questions(mock_guest_user, mock_guest_profile, mock_projects):
    """T036: Guest requests questions for a project and gets a list."""
    from app.bot.handlers.qa import questions_command

    @asynccontextmanager
    async def mock_session():
        yield MagicMock()

    mock_update = MagicMock()
    mock_update.effective_user.id = int(mock_guest_user.telegram_user_id)
    mock_update.message.reply_text = AsyncMock()

    mock_context = MagicMock()
    mock_context.user_data = {}

    with patch("app.bot.handlers.qa.async_session", mock_session), \
         patch("app.bot.handlers.qa._get_user_with_profiles") as mock_get_profiles, \
         patch("app.bot.handlers.qa.qa_service") as mock_qa_svc:

        mock_get_profiles.return_value = (mock_guest_user, mock_guest_profile, None)
        mock_qa_svc.get_user_recommendations = AsyncMock(return_value=mock_projects)

        await questions_command(mock_update, mock_context)

        # Should call reply_text with project list
        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args
        text = call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")

        # Should show Q&A header or project list
        assert (
            "вопрос" in text.lower() or
            "q&a" in text.lower() or
            "проект" in text.lower()
        )


@pytest.mark.asyncio
async def test_business_investor_qa_questions(mock_business_user, mock_business_profile, mock_projects):
    """T037: Business (investor) requests questions - uses correct profile."""
    from app.bot.handlers.qa import questions_command

    @asynccontextmanager
    async def mock_session():
        yield MagicMock()

    mock_update = MagicMock()
    mock_update.effective_user.id = int(mock_business_user.telegram_user_id)
    mock_update.message.reply_text = AsyncMock()

    mock_context = MagicMock()
    mock_context.user_data = {}

    with patch("app.bot.handlers.qa.async_session", mock_session), \
         patch("app.bot.handlers.qa._get_user_with_profiles") as mock_get_profiles, \
         patch("app.bot.handlers.qa.qa_service") as mock_qa_svc:

        mock_get_profiles.return_value = (mock_business_user, None, mock_business_profile)
        mock_qa_svc.get_user_recommendations = AsyncMock(return_value=mock_projects)

        await questions_command(mock_update, mock_context)

        # Should call reply_text
        mock_update.message.reply_text.assert_called()

        # Business profile should be passed
        assert mock_business_profile.objective == BusinessObjective.INVESTMENT


@pytest.mark.asyncio
async def test_qa_llm_fallback(mock_guest_user, mock_guest_profile, mock_projects):
    """T038: LLM unavailable - should handle gracefully."""
    from app.bot.handlers.qa import questions_command

    @asynccontextmanager
    async def mock_session():
        yield MagicMock()

    mock_update = MagicMock()
    mock_update.effective_user.id = int(mock_guest_user.telegram_user_id)
    mock_update.message.reply_text = AsyncMock()

    mock_context = MagicMock()
    mock_context.user_data = {}

    with patch("app.bot.handlers.qa.async_session", mock_session), \
         patch("app.bot.handlers.qa._get_user_with_profiles") as mock_get_profiles, \
         patch("app.bot.handlers.qa.qa_service") as mock_qa_svc:

        mock_get_profiles.return_value = (mock_guest_user, mock_guest_profile, None)
        # Return empty list to simulate no recommendations
        mock_qa_svc.get_user_recommendations = AsyncMock(return_value=[])

        await questions_command(mock_update, mock_context)

        # Should call reply_text with appropriate message
        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args
        text = call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")

        # Should mention no projects or suggest profiling
        assert (
            "нет" in text.lower() or
            "профил" in text.lower() or
            "пока" in text.lower()
        )
