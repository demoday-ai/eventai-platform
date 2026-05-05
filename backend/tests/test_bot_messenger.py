"""Tests for the send-only aiogram.Bot singleton (031-bot-replacement)."""

import pytest

from app.config import settings
from app.services.core import bot_messenger


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Make sure each test starts and ends with a clean module-level singleton."""
    bot_messenger._bot = None
    yield
    bot_messenger._bot = None


def test_get_send_bot_requires_token(monkeypatch):
    """Without BOT_TOKEN, get_send_bot must raise."""
    monkeypatch.setattr(settings, "bot_token", "")
    with pytest.raises(RuntimeError, match="BOT_TOKEN"):
        bot_messenger.get_send_bot()


def test_get_send_bot_returns_singleton(monkeypatch):
    """Second call returns the same Bot instance (no duplicate sessions)."""
    monkeypatch.setattr(settings, "bot_token", "123456:dummy-test-token")
    first = bot_messenger.get_send_bot()
    second = bot_messenger.get_send_bot()
    assert first is second


async def test_close_send_bot_idempotent(monkeypatch):
    """close_send_bot is safe to call without prior get_send_bot."""
    monkeypatch.setattr(settings, "bot_token", "")
    # No singleton yet — should not raise.
    await bot_messenger.close_send_bot()
    assert bot_messenger._bot is None
