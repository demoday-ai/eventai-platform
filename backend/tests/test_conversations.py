"""Tests for unified conversations (chat_messages + thread metadata)."""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.chat_message import ChatMessage
from app.models.event import Event
from app.models.support_thread import SupportThread
from app.models.user import User
from app.services.admin import conversation_service


async def _seed_user_event(session):
    event = Event(name="DD", start_date=date.today(), end_date=date.today())
    user = User(telegram_user_id="g1", full_name="Guest One")
    session.add_all([event, user])
    await session.flush()
    return user, event


class TestGetConversations:
    @pytest.mark.asyncio
    async def test_lists_guest_with_only_chat_messages(self, session):
        """A guest who only chatted with the AI (no /support) still appears."""
        user, event = await _seed_user_event(session)
        base = datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
        session.add_all([
            ChatMessage(user_id=user.id, event_id=event.id, role="user",
                        content="привет", created_at=base),
            ChatMessage(user_id=user.id, event_id=event.id, role="assistant",
                        content="здравствуйте", created_at=base + timedelta(minutes=1)),
        ])
        await session.flush()

        result = await conversation_service.get_conversations(session, event.id, filter="all")
        assert result.total == 1
        conv = result.conversations[0]
        assert conv.user_id == str(user.id)
        assert conv.user_name == "Guest One"
        assert conv.message_count == 2
        assert conv.last_message == "здравствуйте"
        assert conv.needs_attention is False
        assert conv.taken_over is False
        assert conv.unread is False  # last message is assistant

    @pytest.mark.asyncio
    async def test_unread_true_when_last_is_user(self, session):
        user, event = await _seed_user_event(session)
        base = datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
        session.add(ChatMessage(user_id=user.id, event_id=event.id, role="user",
                                content="вопрос", created_at=base))
        await session.flush()
        result = await conversation_service.get_conversations(session, event.id, filter="all")
        assert result.conversations[0].unread is True

    @pytest.mark.asyncio
    async def test_filter_attention(self, session):
        user, event = await _seed_user_event(session)
        base = datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
        session.add(ChatMessage(user_id=user.id, event_id=event.id, role="user",
                                content="x", created_at=base))
        session.add(SupportThread(user_id=user.id, event_id=event.id,
                                  status="open", needs_attention=True))
        await session.flush()
        attn = await conversation_service.get_conversations(session, event.id, filter="attention")
        assert attn.total == 1
        # a guest without needs_attention is excluded
        u2 = User(telegram_user_id="g2", full_name="Guest Two")
        session.add(u2)
        await session.flush()
        session.add(ChatMessage(user_id=u2.id, event_id=event.id, role="user",
                                content="y", created_at=base))
        await session.flush()
        attn2 = await conversation_service.get_conversations(session, event.id, filter="attention")
        assert attn2.total == 1
