"""Tests for support chat: models, service, schemas."""

import uuid

import pytest
from pydantic import ValidationError


class TestSupportThreadModel:
    """SupportThread model should exist with correct fields."""

    def test_create_thread(self):
        from app.models.support_thread import SupportThread

        thread = SupportThread(
            user_id=uuid.uuid4(),
            event_id=uuid.uuid4(),
            status="open",
        )
        assert thread.status == "open"
        assert thread.closed_by is None

    def test_thread_statuses(self):
        from app.models.support_thread import SupportThread

        for s in ("open", "closed"):
            thread = SupportThread(
                user_id=uuid.uuid4(),
                event_id=uuid.uuid4(),
                status=s,
            )
            assert thread.status == s


class TestSupportMessageModel:
    """SupportMessage model should exist with correct fields."""

    def test_create_user_message(self):
        from app.models.support_message import SupportMessage

        msg = SupportMessage(
            thread_id=uuid.uuid4(),
            sender_type="user",
            sender_id=uuid.uuid4(),
            text="Когда мое выступление?",
        )
        assert msg.sender_type == "user"
        assert msg.text == "Когда мое выступление?"

    def test_create_organizer_message(self):
        from app.models.support_message import SupportMessage

        msg = SupportMessage(
            thread_id=uuid.uuid4(),
            sender_type="organizer",
            sender_id=uuid.uuid4(),
            text="Зал 3, 14:00",
        )
        assert msg.sender_type == "organizer"


class TestSupportSchemas:
    """Pydantic schemas for support chat API."""

    def test_thread_response_schema(self):
        from app.schemas.support import ThreadResponse

        t = ThreadResponse(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            user_name="Иван",
            user_username="ivan",
            user_role="student",
            status="open",
            last_message="Привет",
            last_message_at="2026-03-24T12:00:00Z",
            unread=True,
            message_count=3,
        )
        assert t.status == "open"
        assert t.unread is True

    def test_message_response_schema(self):
        from app.schemas.support import MessageResponse

        m = MessageResponse(
            id=str(uuid.uuid4()),
            sender_type="user",
            sender_name="Иван",
            text="Когда мое выступление?",
            created_at="2026-03-24T12:00:00Z",
        )
        assert m.sender_type == "user"

    def test_send_message_request(self):
        from app.schemas.support import SendMessageRequest

        req = SendMessageRequest(text="Зал 3, 14:00")
        assert req.text == "Зал 3, 14:00"

    def test_send_message_requires_text(self):
        from app.schemas.support import SendMessageRequest

        with pytest.raises(ValidationError):
            SendMessageRequest(text="")

    def test_create_thread_request(self):
        from app.schemas.support import CreateThreadRequest

        req = CreateThreadRequest(user_id=str(uuid.uuid4()), message="Привет!")
        assert req.message == "Привет!"


class TestSendOrganizerReply:
    """Service: organizer reply clears the needs_attention flag (ADR-001)."""

    @pytest.mark.asyncio
    async def test_reply_clears_needs_attention(self, session):
        from datetime import date

        from app.models.event import Event
        from app.models.support_thread import SupportThread
        from app.models.user import User
        from app.services.admin import support_service

        event = Event(name="DD", start_date=date.today(), end_date=date.today())
        organizer = User(telegram_user_id="org1", full_name="Org")
        guest = User(telegram_user_id="g1", full_name="Guest")
        session.add_all([event, organizer, guest])
        await session.flush()

        thread = SupportThread(
            user_id=guest.id,
            event_id=event.id,
            status="open",
            needs_attention=True,
        )
        session.add(thread)
        await session.flush()

        await support_service.send_organizer_reply(
            session, thread.id, event.id, organizer.id, "Зал 3, 14:00"
        )

        await session.refresh(thread)
        assert thread.needs_attention is False
