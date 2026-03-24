"""Tests for 'Contact organizers' button in bot."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.bot.keyboards import program_recommendation_keyboard


class TestContactOrganizersButton:
    """Test that program keyboard includes contact organizers button."""

    def test_keyboard_has_contact_organizers_button(self):
        """Program recommendation keyboard should include a 'Связь с организаторами' button."""
        recs = [
            {"rank": 1, "title": "Test Project", "project_id": "abc123456789"},
        ]
        kb = program_recommendation_keyboard(recs)
        all_buttons = [btn.text for row in kb.inline_keyboard for btn in row]
        assert any("организатор" in btn.lower() for btn in all_buttons), (
            f"Expected 'организатор' button in keyboard, got: {all_buttons}"
        )

    def test_contact_organizers_callback_data(self):
        """Contact organizers button should have correct callback_data prefix."""
        recs = [
            {"rank": 1, "title": "Test Project", "project_id": "abc123456789"},
        ]
        kb = program_recommendation_keyboard(recs)
        all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert any(d.startswith("contact:organizers") for d in all_data), (
            f"Expected 'contact:organizers' callback_data, got: {all_data}"
        )
