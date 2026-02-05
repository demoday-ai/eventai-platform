"""E2E test fixtures using Telethon.

To run e2e tests, you need:
1. api_id and api_hash from https://my.telegram.org
2. A session string (run `python tests/e2e/generate_session.py` to create one)
3. Set environment variables or create .env.e2e file

Required env vars:
- TELEGRAM_API_ID
- TELEGRAM_API_HASH
- TELEGRAM_SESSION_STRING
- TEST_BOT_USERNAME (default: demoday_ai_talent_hub_test_bot)
"""

import asyncio
import os
from time import sleep

import pytest
import pytest_asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

# Load from .env.e2e if exists
try:
    from dotenv import load_dotenv
    load_dotenv("tests/e2e/.env.e2e")
except ImportError:
    pass

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING")
BOT_USERNAME = os.getenv("TEST_BOT_USERNAME", "demoday_ai_talent_hub_test_bot")
DELAY = 0.5  # seconds between actions


def skip_if_no_credentials():
    """Skip test if Telegram credentials not configured."""
    if not all([API_ID, API_HASH, SESSION_STRING]):
        pytest.skip("Telegram e2e credentials not configured")


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def telegram_client(event_loop):
    """Connect to Telegram as a user."""
    skip_if_no_credentials()

    client = TelegramClient(
        StringSession(SESSION_STRING),
        int(API_ID),
        API_HASH,
        sequential_updates=True,
        loop=event_loop,
    )
    await client.connect()

    if not await client.is_user_authorized():
        pytest.skip("Telegram session expired, regenerate with generate_session.py")

    yield client
    await client.disconnect()


@pytest_asyncio.fixture(scope="function")
async def conv(telegram_client):
    """Open conversation with the bot."""
    async with telegram_client.conversation(
        BOT_USERNAME,
        timeout=30,
        max_messages=10000,
    ) as conv:
        yield conv


def wait(seconds: float = DELAY):
    """Fixed delay to handle network latency."""
    sleep(seconds)


def get_button_with_text(message, text: str, strict: bool = False):
    """Find button by text in message."""
    if message.buttons is None:
        return None
    for row in message.buttons:
        for button in row:
            is_match = (text == button.text) if strict else (text in button.text)
            if is_match:
                return button
    return None


async def click_button(conv, message, text: str, strict: bool = False):
    """Click button and return response."""
    button = get_button_with_text(message, text, strict)
    if button is None:
        raise ValueError(f"Button '{text}' not found in message")
    await button.click()
    wait()
    return await conv.get_edit()
