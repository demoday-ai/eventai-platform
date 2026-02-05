"""Interactive session generator - run in terminal manually."""
import asyncio
import os

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

load_dotenv("tests/e2e/.env.e2e")

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")

async def main():
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start()
    session_string = client.session.save()
    print("\n" + "=" * 60)
    print("SESSION STRING (скопируй это):")
    print("=" * 60)
    print(session_string)
    print("=" * 60)
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
