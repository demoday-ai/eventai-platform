"""
Telegram-бот: логирует все сообщения группового чата в messages.json.
При @mention бота помечает сообщение как ожидающее ответа в pending.json.
Claude Code читает эти файлы и отвечает через send.py.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

load_dotenv()

BASE_DIR = Path(__file__).parent
MESSAGES_FILE = BASE_DIR / "messages.json"
PENDING_FILE = BASE_DIR / "pending.json"
CHAT_CONFIG_FILE = BASE_DIR / "chat_config.json"


def load_json(path: Path) -> list:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_chat_id(chat_id: int, chat_title: str | None):
    config = {}
    if CHAT_CONFIG_FILE.exists():
        with open(CHAT_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    if config.get("chat_id") != chat_id:
        config["chat_id"] = chat_id
        config["chat_title"] = chat_title
        save_json(CHAT_CONFIG_FILE, config)
        print(f"Chat ID: {chat_id} ({chat_title})")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message:
        return

    save_chat_id(message.chat_id, message.chat.title)

    # Данные сообщения
    reply_to = None
    if message.reply_to_message:
        reply_to = {
            "id": message.reply_to_message.message_id,
            "from": message.reply_to_message.from_user.first_name if message.reply_to_message.from_user else None,
            "text": message.reply_to_message.text or message.reply_to_message.caption,
        }

    text = message.text or message.caption or "[media]"

    entry = {
        "id": message.message_id,
        "date": message.date.isoformat(),
        "from": message.from_user.first_name if message.from_user else None,
        "username": message.from_user.username if message.from_user else None,
        "text": text,
        "reply_to": reply_to,
    }

    # Сохраняем в общий лог
    messages = load_json(MESSAGES_FILE)
    messages.append(entry)
    save_json(MESSAGES_FILE, messages)

    print(f"[{entry['date']}] {entry['from']}: {text[:80]}")

    # Если @mention бота -- добавляем в pending
    bot_username = context.bot.username
    if bot_username and f"@{bot_username}" in text:
        question = text.replace(f"@{bot_username}", "").strip()
        pending_entry = {
            **entry,
            "question": question if question else text,
        }
        pending = load_json(PENDING_FILE)
        pending.append(pending_entry)
        save_json(PENDING_FILE, pending)
        print(f"*** PENDING: {entry['from']} asks: {question[:80]}")


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("BOT_TOKEN not found in .env")
        return

    print("Bot started. Logging messages...")
    print("@mention trigger -> saves to pending.json")
    print("Tell Claude Code 'check chat' to respond")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
