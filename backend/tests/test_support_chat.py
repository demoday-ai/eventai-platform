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
