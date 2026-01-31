"""
Отправляет сообщение в групповой чат от имени бота.

Использование:
    python send.py "Текст сообщения"
    python send.py "Ответ на сообщение" --reply-to 123
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

BASE_DIR = Path(__file__).parent
CHAT_CONFIG_FILE = BASE_DIR / "chat_config.json"


async def send_message(text: str, reply_to: int | None = None):
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("Ошибка: BOT_TOKEN не найден в .env")
        sys.exit(1)

    if not CHAT_CONFIG_FILE.exists():
        print("Ошибка: chat_config.json не найден.")
        print("Сначала запусти bot.py и напиши что-нибудь в чат,")
        print("чтобы бот узнал chat_id.")
        sys.exit(1)

    with open(CHAT_CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    chat_id = config["chat_id"]
    bot = Bot(token=token)

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_to_message_id=reply_to,
    )
    print(f"Отправлено в {config.get('chat_title', chat_id)}")


def main():
    parser = argparse.ArgumentParser(description="Отправить сообщение в групповой чат")
    parser.add_argument("text", help="Текст сообщения")
    parser.add_argument("--reply-to", type=int, default=None, help="ID сообщения для ответа")
    args = parser.parse_args()

    asyncio.run(send_message(args.text, args.reply_to))


if __name__ == "__main__":
    main()
