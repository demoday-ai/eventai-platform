"""Tests for pre-slot reminders: 30 min instead of 1 hour, both students and experts."""

from unittest.mock import MagicMock

from app.services.admin.notification_service import build_pre_slot_reminder


class TestPreSlotReminder:
    """Pre-slot reminder should say '30 минут' not 'час'."""

    def _make_slot(self):
        slot = MagicMock()
        slot.start_time = "10:30"
        return slot

    def _make_room(self, name="Зал 1"):
        room = MagicMock()
        room.name = name
        return room

    def test_student_reminder_says_30_min(self):
        user = MagicMock()
        msg = build_pre_slot_reminder(user, "student", self._make_slot(), self._make_room())
        assert "30 минут" in msg or "30 мин" in msg
        assert "час" not in msg.lower()

    def test_expert_reminder_says_30_min(self):
        user = MagicMock()
        msg = build_pre_slot_reminder(user, "expert", self._make_slot(), self._make_room())
        assert "30 минут" in msg or "30 мин" in msg
        assert "час" not in msg.lower()

    def test_guest_reminder_says_30_min(self):
        user = MagicMock()
        msg = build_pre_slot_reminder(user, "guest", self._make_slot(), self._make_room(), "Test Project")
        assert "30 минут" in msg or "30 мин" in msg

    def test_student_reminder_mentions_room(self):
        user = MagicMock()
        msg = build_pre_slot_reminder(user, "student", self._make_slot(), self._make_room("Зал NLP"))
        assert "Зал NLP" in msg

    def test_expert_reminder_mentions_room(self):
        user = MagicMock()
        msg = build_pre_slot_reminder(user, "expert", self._make_slot(), self._make_room("Зал CV"))
        assert "Зал CV" in msg
