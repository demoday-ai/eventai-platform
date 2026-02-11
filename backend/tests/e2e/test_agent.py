#!/usr/bin/env python3
"""Quick test for agent mode after persistence fix."""

import asyncio
import os
import sys

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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


async def navigate_to_program(conv):
    """Navigate existing user to VIEW_PROGRAM state."""
    print("\n[SETUP] Navigating to VIEW_PROGRAM state...")

    # Send /start
    await conv.send_message("/start")
    await asyncio.sleep(2)
    msg = await conv.get_response()
    print(f"  /start response: {msg.text[:80] if msg.text else 'no text'}...")

    # If returning user, click "Нет, оставить"
    keep_btn = get_button(msg, "оставить")
    if keep_btn:
        await keep_btn.click()
        await asyncio.sleep(2)
        msg = await conv.get_response()
        print(f"  After keep role: {msg.text[:80] if msg.text else 'no text'}...")

    # Look for "Получить программу" button
    program_btn = get_button(msg, "программу") or get_button(msg, "Получить")
    if program_btn:
        print(f"  Clicking: {program_btn.text}")
        await program_btn.click()
        await asyncio.sleep(8)  # LLM needs time to generate
        msg = await conv.get_response()
        print(f"  After generate: {msg.text[:100] if msg.text else 'no text'}...")
        return msg

    # Maybe profile not complete, try profiling
    profiling_btn = get_button(msg, "профилирование")
    if profiling_btn:
        print(f"  Clicking: {profiling_btn.text}")
        await profiling_btn.click()
        await asyncio.sleep(2)
        msg = await conv.get_response()
        print(f"  Profiling response: {msg.text[:80] if msg.text else 'no text'}...")

    return msg


async def main():
    print("=" * 60)
    print("Agent Mode Test (after Persistence fix)")
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
        async with client.conversation(BOT_USERNAME, timeout=60) as conv:
            # First navigate to VIEW_PROGRAM state
            await navigate_to_program(conv)

            # Now test agent mode query
            print("\n[TEST] Agent mode query: 'покажи мой профиль'")
            await conv.send_message("покажи мой профиль")
            await asyncio.sleep(8)  # LLM needs time

            try:
                msg = await asyncio.wait_for(conv.get_response(), timeout=15)
                print(f"  Response: {msg.text[:200] if msg.text else 'no text'}...")

                if msg.text and len(msg.text) > 20:
                    print("  [PASS] Got response from agent mode!")
                else:
                    print("  [WARN] Response seems short")
            except asyncio.TimeoutError:
                print("  [FAIL] No response - agent mode not working")
                return 1

        print("\n" + "=" * 60)
        print("TESTS COMPLETED")
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
