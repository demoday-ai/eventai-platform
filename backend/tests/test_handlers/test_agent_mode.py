"""Tests for agent mode with tool calling in VIEW_PROGRAM state.

Uses PTB's process_update to inject fake updates without Telegram API.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from app.bot.handlers.guest_profiling import (
    AGENT_TOOLS,
    VIEW_PROGRAM,
    _format_if_time,
    _format_recommendations,
    view_program_text,
)


def make_fake_message(text: str, user_id: int = 123456789) -> MagicMock:
    """Create a fake Telegram message using MagicMock."""
    user = User(id=user_id, is_bot=False, first_name="Test")
    chat = Chat(id=user_id, type="private")
    message = MagicMock(spec=Message)
    message.message_id = 1
    message.date = None
    message.chat = chat
    message.from_user = user
    message.text = text
    message.reply_text = AsyncMock()
    return message


def make_fake_update(text: str, user_id: int = 123456789) -> MagicMock:
    """Create a fake Telegram update with a message."""
    message = make_fake_message(text, user_id)
    update = MagicMock(spec=Update)
    update.update_id = 1
    update.message = message
    return update


class TestAgentTools:
    """Test AGENT_TOOLS definition."""

    def test_agent_tools_defined(self):
        """Verify AGENT_TOOLS has expected tools."""
        assert len(AGENT_TOOLS) == 3

        tool_names = [t["function"]["name"] for t in AGENT_TOOLS]
        assert "rebuild_profile" in tool_names
        assert "show_project" in tool_names
        assert "show_profile" in tool_names

    def test_rebuild_profile_tool_schema(self):
        """Verify rebuild_profile tool has correct schema."""
        tool = next(t for t in AGENT_TOOLS if t["function"]["name"] == "rebuild_profile")
        assert tool["type"] == "function"
        assert "description" in tool["function"]
        assert "профил" in tool["function"]["description"].lower()

    def test_show_project_tool_schema(self):
        """Verify show_project tool has project_rank parameter."""
        tool = next(t for t in AGENT_TOOLS if t["function"]["name"] == "show_project")
        params = tool["function"]["parameters"]
        assert "project_rank" in params["properties"]
        assert params["properties"]["project_rank"]["type"] == "integer"

    def test_show_profile_tool_schema(self):
        """Verify show_profile tool has no required parameters."""
        tool = next(t for t in AGENT_TOOLS if t["function"]["name"] == "show_profile")
        params = tool["function"]["parameters"]
        assert params["required"] == []


class TestFormatRecommendations:
    """Test recommendation formatting functions."""

    def test_format_recommendations_basic(self):
        """Test basic recommendation formatting."""
        data = {
            "must_visit": [
                {
                    "rank": 1,
                    "title": "Test Project",
                    "summary": "A test project summary",
                    "room_number": 1,
                    "tags": ["NLP", "LLM"],
                    "relevance_score": 85,
                    "conflict_rooms": [],
                    "project_id": str(uuid4()),
                },
            ],
            "if_time": [],
            "total": 1,
        }

        messages = _format_recommendations(data)
        assert len(messages) >= 1
        assert "Test Project" in messages[0]
        assert "85%" in messages[0]
        assert "Топ-рекомендации" in messages[0]

    def test_format_recommendations_no_emoji(self):
        """Verify no emoji in formatted output."""
        data = {
            "must_visit": [
                {
                    "rank": 1,
                    "title": "Test",
                    "summary": "Summary",
                    "room_number": 1,
                    "tags": ["NLP"],
                    "relevance_score": 90,
                    "conflict_rooms": [],
                    "project_id": str(uuid4()),
                },
            ],
            "if_time": [],
            "total": 1,
        }

        messages = _format_recommendations(data)
        text = "".join(messages)
        # Should not contain common emoji
        assert "🎯" not in text
        assert "📍" not in text
        assert "⚠️" not in text

    def test_format_if_time_basic(self):
        """Test if_time formatting."""
        data = {
            "must_visit": [],
            "if_time": [
                {
                    "rank": 6,
                    "title": "Secondary Project",
                    "summary": "Less important",
                    "room_number": 2,
                    "tags": ["CV"],
                    "relevance_score": 60,
                    "project_id": str(uuid4()),
                },
            ],
            "total": 1,
        }

        messages = _format_if_time(data)
        assert len(messages) >= 1
        assert "Secondary Project" in messages[0]
        assert "Дополнительно" in messages[0]


class TestViewProgramText:
    """Test view_program_text handler with mocked LLM."""

    @pytest.fixture
    def mock_context(self):
        """Create mock context with user_data."""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {
            "profile_user_id": str(uuid4()),
            "profile_event_id": str(uuid4()),
            "profile_id": str(uuid4()),
            "recommendations": {
                "must_visit": [
                    {
                        "rank": 1,
                        "title": "AI Project",
                        "summary": "An AI project",
                        "room_number": 1,
                        "tags": ["NLP"],
                        "relevance_score": 90,
                        "project_id": str(uuid4()),
                    },
                ],
                "if_time": [],
                "total": 1,
            },
            "program_chat": [],
        }
        context.bot = AsyncMock()
        context.bot.send_chat_action = AsyncMock()
        return context

    @pytest.mark.asyncio
    async def test_view_program_text_calls_llm(self, mock_context):
        """Test that view_program_text calls LLM with tools."""
        update = make_fake_update("покажи мой профиль")

        with patch("app.services.llm_client") as mock_llm, \
             patch("app.bot.handlers.guest_profiling.async_session") as mock_session, \
             patch("app.bot.handlers.guest_profiling.profiling_service") as mock_prof:

            # Mock LLM response
            mock_llm.send_chat_with_tools = AsyncMock(return_value={
                "type": "text",
                "content": "Ваш профиль: интересы NLP",
            })

            # Mock profile
            mock_profile = MagicMock()
            mock_profile.selected_tags = ["NLP"]
            mock_profile.keywords = []
            mock_profile.extra_data = None
            mock_prof.get_or_create_profile = AsyncMock(return_value=mock_profile)

            # Mock session context manager
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await view_program_text(update, mock_context)

            # Verify LLM was called with tools
            mock_llm.send_chat_with_tools.assert_called_once()
            call_args = mock_llm.send_chat_with_tools.call_args
            assert call_args.kwargs["tools"] == AGENT_TOOLS

            # Verify reply was sent
            update.message.reply_text.assert_called()
            assert result == VIEW_PROGRAM

    @pytest.mark.asyncio
    async def test_view_program_text_tool_show_profile(self, mock_context):
        """Test show_profile tool execution."""
        update = make_fake_update("покажи профиль")

        with patch("app.services.llm_client") as mock_llm, \
             patch("app.bot.handlers.guest_profiling.async_session") as mock_session, \
             patch("app.bot.handlers.guest_profiling.profiling_service") as mock_prof:

            # LLM returns tool call
            mock_llm.send_chat_with_tools = AsyncMock(return_value={
                "type": "tool_call",
                "tool_name": "show_profile",
                "tool_args": {},
            })

            mock_profile = MagicMock()
            mock_profile.selected_tags = ["CV", "NLP"]
            mock_profile.keywords = ["компьютерное зрение"]
            mock_profile.extra_data = {"nl_summary": "Студент, интересуется CV"}
            mock_prof.get_or_create_profile = AsyncMock(return_value=mock_profile)

            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await view_program_text(update, mock_context)

            # Should reply with profile info
            update.message.reply_text.assert_called()
            reply_text = update.message.reply_text.call_args[0][0]
            assert "профиль" in reply_text.lower() or "теги" in reply_text.lower()
            assert result == VIEW_PROGRAM
