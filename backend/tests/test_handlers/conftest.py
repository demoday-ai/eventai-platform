"""Handler smoke tests fixtures.

Provides mock factories and fixtures for testing Telegram bot handlers.
Based on research.md patterns for python-telegram-bot 21.x.

Note: These smoke tests use mock objects instead of a real database because
PostgreSQL-specific types (ARRAY, JSONB) don't work with SQLite in-memory DB.
"""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from telegram import Bot
from telegram.ext import ApplicationBuilder

from app.models.role import RoleCode

# =============================================================================
# Mock Update Factories (T004, T005)
# =============================================================================

@pytest.fixture(scope="session")
def make_message_update():
    """Factory for creating message Update dicts."""
    def _make(
        user_id: int,
        chat_id: int,
        text: str,
        update_id: int = 1,
        message_id: int = 1,
        first_name: str = "Test",
        username: str = "test_user",
    ) -> dict:
        return {
            "update_id": update_id,
            "message": {
                "message_id": message_id,
                "date": int(datetime.now(timezone.utc).timestamp()),
                "chat": {"id": chat_id, "type": "private"},
                "from": {
                    "id": user_id,
                    "is_bot": False,
                    "first_name": first_name,
                    "username": username,
                },
                "text": text,
            },
        }
    return _make


@pytest.fixture(scope="session")
def make_callback_update():
    """Factory for creating callback query Update dicts."""
    def _make(
        user_id: int,
        chat_id: int,
        callback_data: str,
        update_id: int = 1,
        message_id: int = 1,
        first_name: str = "Test",
        username: str = "test_user",
    ) -> dict:
        return {
            "update_id": update_id,
            "callback_query": {
                "id": f"query_{update_id}_{uuid.uuid4().hex[:8]}",
                "from": {
                    "id": user_id,
                    "is_bot": False,
                    "first_name": first_name,
                    "username": username,
                },
                "chat_instance": str(chat_id),
                "data": callback_data,
                "message": {
                    "message_id": message_id,
                    "date": int(datetime.now(timezone.utc).timestamp()),
                    "chat": {"id": chat_id, "type": "private"},
                    "from": {"id": 0, "is_bot": True, "first_name": "Bot"},
                    "text": "Previous message",
                },
            },
        }
    return _make


# =============================================================================
# Application Fixture (T006)
# =============================================================================

@pytest_asyncio.fixture
async def app():
    """Create test Application with registered handlers.

    Mocks get_me() to avoid real API calls during initialization.
    """
    # Mock the get_me call that happens during initialization
    mock_user = MagicMock()
    mock_user.id = 123456789
    mock_user.is_bot = True
    mock_user.first_name = "TestBot"
    mock_user.username = "test_bot"
    mock_user.can_join_groups = True
    mock_user.can_read_all_group_messages = False
    mock_user.supports_inline_queries = False

    with patch.object(Bot, "get_me", new_callable=AsyncMock) as mock_get_me:
        mock_get_me.return_value = mock_user

        # Use a fake token for testing
        application = ApplicationBuilder().token("0:TEST_TOKEN_FOR_TESTING").build()

        # Import and register handlers
        from app.bot.handlers.guest_profiling import get_profiling_handler
        from app.bot.handlers.qa import get_qa_handlers
        from app.bot.handlers.start import get_onboarding_handler

        application.add_handler(get_onboarding_handler())
        application.add_handler(get_profiling_handler())

        for handler in get_qa_handlers():
            application.add_handler(handler)

        await application.initialize()
        yield application
        await application.shutdown()


# =============================================================================
# Bot Method Mocks (T007)
# =============================================================================

@pytest.fixture
def mock_bot_methods():
    """Mock bot methods to capture responses without sending real messages.

    Note: Handlers use update.message.reply_text() which internally calls
    bot.send_message(), so we patch at the Bot level.
    """
    mock_message = MagicMock()
    mock_message.message_id = 1

    with patch.object(Bot, "send_message", new_callable=AsyncMock) as send_msg, \
         patch.object(Bot, "edit_message_text", new_callable=AsyncMock) as edit_msg, \
         patch.object(Bot, "answer_callback_query", new_callable=AsyncMock) as answer, \
         patch.object(Bot, "send_chat_action", new_callable=AsyncMock) as action:

        # Configure return values to return proper message objects
        send_msg.return_value = mock_message
        edit_msg.return_value = mock_message
        answer.return_value = True
        action.return_value = True

        yield {
            "send_message": send_msg,
            "edit_message_text": edit_msg,
            "answer_callback_query": answer,
            "send_chat_action": action,
        }


# =============================================================================
# Database Fixtures (T008, T009)
# Note: Using mock objects instead of real DB for smoke tests
# (PostgreSQL-specific types like ARRAY/JSONB don't work with SQLite)
# =============================================================================

@pytest.fixture
def db_session():
    """Provide mock database session for tests.

    For smoke tests, we mock the service layer rather than using a real DB.
    """
    return MagicMock()


@pytest.fixture
def test_roles():
    """Create mock roles for testing."""
    roles = {}
    for role_code in RoleCode:
        role = MagicMock()
        role.id = uuid.uuid4()
        role.code = role_code.value
        role.name = role_code.value.capitalize()
        roles[role_code.value] = role
    return roles


@pytest.fixture
def test_event():
    """Create mock Demo Day event."""
    event = MagicMock()
    event.id = uuid.uuid4()
    event.name = "Demo Day Test"
    event.start_date = date.today()
    event.end_date = date.today()
    event.is_active = True
    return event


# =============================================================================
# LLM Mocks (T010, T011)
# =============================================================================

@pytest.fixture
def mock_llm():
    """Mock LLM client with predefined responses."""
    async def fake_llm(*args, **kwargs):
        # Return predefined responses based on context
        return {
            "projects": [{"id": "test-1", "score": 90}],
            "questions": ["Какую проблему решает ваш проект?", "Какие технологии используете?"],
            "tags": ["NLP", "LLM"],
            "keywords": ["чат-бот", "генерация"],
        }

    with patch("app.services.llm_client.send_chat_completion", side_effect=fake_llm) as mock:
        yield mock


@pytest.fixture
def mock_llm_unavailable():
    """Mock LLM client to simulate unavailability."""
    with patch(
        "app.services.llm_client.send_chat_completion",
        side_effect=Exception("LLM unavailable")
    ) as mock:
        yield mock


# =============================================================================
# User Fixtures (T016, T023)
# =============================================================================

@pytest.fixture
def registered_guest(test_roles, test_event):
    """Create a mock user with guest role."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.telegram_user_id = "200"
    user.full_name = "Test Guest"
    user.username = "guest_user"
    user.roles = [MagicMock(role=test_roles["guest"])]
    return user


@pytest.fixture
def registered_business(test_roles, test_event):
    """Create a mock user with business role."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.telegram_user_id = "300"
    user.full_name = "Test Business"
    user.username = "biz_user"
    user.roles = [MagicMock(role=test_roles["business"])]
    return user


# =============================================================================
# Profile Fixtures (T017, T024)
# =============================================================================

@pytest.fixture
def guest_with_profile(registered_guest, test_event):
    """Create a guest with filled GuestProfile mock."""
    profile = MagicMock()
    profile.id = uuid.uuid4()
    profile.user_id = registered_guest.id
    profile.event_id = test_event.id
    profile.selected_tags = ["NLP", "CV"]
    profile.extracted_tags = ["LLM"]
    profile.keywords = ["чат-бот"]
    return registered_guest, profile


# =============================================================================
# Tags and Projects Fixtures (T018, T029, T030)
# =============================================================================

@pytest.fixture
def test_tags():
    """Create mock tags for testing."""
    tag_names = ["NLP", "CV", "LLM", "FinTech", "EdTech", "Agents", "ML", "ASR"]
    tags = []

    for name in tag_names:
        tag = MagicMock()
        tag.id = uuid.uuid4()
        tag.name = name
        tags.append(tag)

    return tags


@pytest.fixture
def test_projects(test_event):
    """Create mock test projects."""
    projects = []

    for i in range(5):
        project = MagicMock()
        project.id = uuid.uuid4()
        project.title = f"Test Project {i+1}"
        project.description = f"Description for project {i+1}"
        project.author = f"Author {i+1}"
        project.telegram_contact = f"@author{i+1}"
        project.event_id = test_event.id
        project.tags = []
        projects.append(project)

    return projects


# =============================================================================
# Service Layer Mocks for Handlers
# =============================================================================

@pytest.fixture
def override_db_session(test_event, test_roles):
    """Override the service layer used by handlers.

    Since handlers call services which use async_session, we mock at the
    service level for true isolation.
    """
    from contextlib import asynccontextmanager

    mock_session = MagicMock()

    @asynccontextmanager
    async def mock_async_session():
        yield mock_session

    with patch("app.database.async_session", mock_async_session):
        # Also patch user_service to return test data
        with patch("app.bot.handlers.start.user_service") as mock_user_svc:
            mock_user_svc.get_current_event = AsyncMock(return_value=test_event)
            mock_user_svc.get_user_role_with_info = AsyncMock(return_value=None)
            mock_user_svc.upsert_user = AsyncMock(return_value=MagicMock(id=uuid.uuid4()))
            mock_user_svc.get_role_by_code = AsyncMock(return_value=test_roles.get("guest"))
            yield mock_session


# =============================================================================
# Test Users Constants
# =============================================================================

TEST_USERS = {
    "new_user": {"id": 100, "username": "new_user", "first_name": "Новый"},
    "guest": {"id": 200, "username": "guest_user", "first_name": "Гость"},
    "business": {"id": 300, "username": "biz_user", "first_name": "Партнёр"},
    "organizer": {"id": 400, "username": "org_user", "first_name": "Орг"},
}
