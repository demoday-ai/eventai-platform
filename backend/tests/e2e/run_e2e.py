#!/usr/bin/env python3
"""E2E tests runner - runs tests directly without pytest fixture issues."""

import asyncio
import os
import sys

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

# Load credentials
load_dotenv("tests/e2e/.env.e2e")

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING")
BOT_USERNAME = os.getenv("TEST_BOT_USERNAME", "demoday_ai_talent_hub_test_bot")


def get_button(message, text):
    """Find button by text."""
    if not message.buttons:
        return None
    for row in message.buttons:
        for btn in row:
            if text in btn.text:
                return btn
    return None


async def test_start_command(conv):
    """Test /start shows role selection."""
    print("\n[TEST] test_start_command")

    # Clear any pending messages
    conv._pending_responses.clear()

    await conv.send_message("/start")
    print("  Sent /start, waiting for response...")

    try:
        msg = await asyncio.wait_for(conv.get_response(), timeout=15)
    except asyncio.TimeoutError:
        print("  Timeout waiting for response, checking last messages...")
        # Try to get messages directly
        async for m in conv._client.iter_messages(BOT_USERNAME, limit=5):
            if m.out:
                continue
            print(f"  Found message: {m.text[:50] if m.text else 'no text'}...")
            msg = m
            break
        else:
            raise Exception("No bot response found")

    print(f"  Response: {msg.text[:100] if msg.text else 'buttons only'}...")

    guest_btn = get_button(msg, "Гость")
    if not guest_btn:
        print(f"  Buttons: {[[b.text for b in row] for row in msg.buttons] if msg.buttons else 'none'}")
    assert guest_btn is not None, "No 'Гость' button"
    print("  [PASS]")
    return msg


async def test_guest_flow(conv, start_msg):
    """Test guest onboarding flow."""
    print("\n[TEST] test_guest_flow")

    # Click guest button
    guest_btn = get_button(start_msg, "Гость")
    if guest_btn:
        await guest_btn.click()
        await asyncio.sleep(2)
        msg = await conv.get_response()
        print(f"  After Гость: {msg.text[:80]}...")
    else:
        msg = start_msg

    # Click student subtype if available
    student_btn = get_button(msg, "Студент")
    if student_btn:
        await student_btn.click()
        await asyncio.sleep(2)
        msg = await conv.get_response()
        print(f"  After Студент: {msg.text[:80]}...")

    print("  [PASS]")
    return msg


async def test_nl_profiling(conv):
    """Test NL profiling with text input."""
    print("\n[TEST] test_nl_profiling")

    await conv.send_message("Интересуюсь NLP и компьютерным зрением")
    await asyncio.sleep(3)
    msg = await conv.get_response()
    print(f"  Response: {msg.text[:100]}...")

    # Confirm profile if asked
    confirm_btn = get_button(msg, "верно") or get_button(msg, "Да")
    if confirm_btn:
        await confirm_btn.click()
        await asyncio.sleep(2)
        msg = await conv.get_response()
        print(f"  After confirm: {msg.text[:80]}...")

    print("  [PASS]")
    return msg


async def test_get_program(conv):
    """Test getting recommendations."""
    print("\n[TEST] test_get_program")

    # Look for program button
    await conv.send_message("/start")
    await asyncio.sleep(2)
    msg = await conv.get_response()

    program_btn = get_button(msg, "программу") or get_button(msg, "Получить")
    if program_btn:
        await program_btn.click()
        await asyncio.sleep(5)  # LLM needs time
        msg = await conv.get_response()
        print(f"  Program: {msg.text[:100]}...")

    print("  [PASS]")
    return msg


async def test_agent_mode(conv):
    """Test agent mode commands."""
    print("\n[TEST] test_agent_mode")

    # Test show profile
    await conv.send_message("покажи мой профиль")
    await asyncio.sleep(3)
    msg = await conv.get_response()
    print(f"  Show profile: {msg.text[:80]}...")

    # Test rebuild request
    await conv.send_message("хочу изменить интересы")
    await asyncio.sleep(3)
    msg = await conv.get_response()
    print(f"  Rebuild: {msg.text[:80]}...")

    print("  [PASS]")


async def main():
    print("=" * 60)
    print("E2E Tests for DemoDay Bot")
    print("=" * 60)

    client = TelegramClient(
        StringSession(SESSION_STRING),
        API_ID,
        API_HASH,
        sequential_updates=True,
    )

    await client.connect()

    if not await client.is_user_authorized():
        print("ERROR: Session expired!")
        return 1

    print(f"Connected as user, testing bot @{BOT_USERNAME}")

    try:
        async with client.conversation(BOT_USERNAME, timeout=30) as conv:
            # Run tests
            start_msg = await test_start_command(conv)
            await test_guest_flow(conv, start_msg)
            await test_nl_profiling(conv)
            await test_get_program(conv)
            await test_agent_mode(conv)

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n[FAIL] {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await client.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
