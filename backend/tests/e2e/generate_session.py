#!/usr/bin/env python3
"""Generate Telegram session string for e2e tests.

Run this script once to authenticate and get a session string.
You'll need to enter your phone number and the code Telegram sends.

Usage:
    python tests/e2e/generate_session.py

Then save the session string to .env.e2e or environment variable.
"""

import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession


async def main():
    print("=" * 60)
    print("Telegram Session String Generator")
    print("=" * 60)
    print()
    print("Get your API credentials from https://my.telegram.org")
    print()

    api_id = input("Enter your API ID: ").strip()
    api_hash = input("Enter your API Hash: ").strip()

    async with TelegramClient(StringSession(), int(api_id), api_hash) as client:
        print()
        print("Session string (save this!):")
        print("-" * 60)
        print(client.session.save())
        print("-" * 60)
        print()
        print("Add to tests/e2e/.env.e2e:")
        print(f"TELEGRAM_API_ID={api_id}")
        print(f"TELEGRAM_API_HASH={api_hash}")
        print(f"TELEGRAM_SESSION_STRING={client.session.save()}")


if __name__ == "__main__":
    asyncio.run(main())
