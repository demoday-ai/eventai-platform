"""End-to-end bot tester via Pyrogram user account.

Loads Telegram session from ~/.config/eventai-test-session.json (created by
/tmp/tg_login_2fa.py during one-time login). Talks to @demoday_ai_talent_hub_test_bot
on the LIVE prod Telegram, so this exercises real message delivery, real
inline buttons, real document attachments.

Usage:
    python bot/scripts/telegram_e2e.py send '/start'
    python bot/scripts/telegram_e2e.py click 'role:guest:student'
    python bot/scripts/telegram_e2e.py last
    python bot/scripts/telegram_e2e.py wait        # poll until next bot message arrives
    python bot/scripts/telegram_e2e.py flow guest  # canned end-to-end scenario

Outputs are printed line-by-line in PIPE format compatible with botchat.sh:
    BOT: <text>
    BUTTON: [<text>] @<callback_data>
    DOCUMENT: <filename> (<size> bytes) [<caption>]
"""
import asyncio
import json
import sys
from pathlib import Path

from pyrogram import Client
from pyrogram.types import Message

API_ID = 31555861
API_HASH = "1fa7744922a60afef71c5b5ec6a9c64a"
STATE_FILE = Path.home() / ".config" / "eventai-test-session.json"
BOT_USERNAME = "demoday_ai_talent_hub_test_bot"


def _load_session() -> str:
    if not STATE_FILE.exists():
        sys.exit(f"No session at {STATE_FILE}. Run /tmp/tg_login_2fa.py first.")
    return json.loads(STATE_FILE.read_text())["session_string"]


def _print_message(msg: Message) -> None:
    """Print a bot message in PIPE format."""
    if msg.document:
        size = msg.document.file_size or 0
        name = msg.document.file_name or "<unnamed>"
        caption = msg.caption or ""
        print(f"DOCUMENT: {name} ({size} bytes) {caption}".rstrip(), flush=True)
    elif msg.text:
        text = msg.text
        # Edits are flagged via msg.edit_date; aiogram answer_text shows as plain text here.
        prefix = "BOT_EDIT" if msg.edit_date else "BOT"
        print(f"{prefix}: {text}", flush=True)
    if msg.reply_markup and hasattr(msg.reply_markup, "inline_keyboard"):
        for row in msg.reply_markup.inline_keyboard:
            for btn in row:
                cb = getattr(btn, "callback_data", None) or ""
                print(f"BUTTON: [{btn.text}] @{cb}", flush=True)
    print("---", flush=True)


async def _wait_for_reply(
    app: Client,
    after_message_id: int,
    timeout: float = 30.0,
    expected_count: int = 1,
) -> list[Message]:
    """Poll get_chat_history until we see expected_count new bot messages
    after `after_message_id`. Returns chronological list (oldest first).
    """
    deadline = asyncio.get_event_loop().time() + timeout
    seen_ids: set[int] = set()
    collected: list[Message] = []
    bot_id = (await app.get_users(BOT_USERNAME)).id

    while asyncio.get_event_loop().time() < deadline:
        new = []
        async for m in app.get_chat_history(BOT_USERNAME, limit=20):
            if m.id <= after_message_id:
                break
            if m.from_user and m.from_user.id == bot_id and m.id not in seen_ids:
                seen_ids.add(m.id)
                new.append(m)
        if new:
            existing_ids = {m.id for m in collected}
            collected.extend(m for m in new if m.id not in existing_ids)
            collected.sort(key=lambda x: x.id)
            if len(collected) >= expected_count:
                return collected
        await asyncio.sleep(1.0)
    return sorted(collected, key=lambda x: x.id)


async def cmd_send(app: Client, text: str) -> None:
    sent = await app.send_message(BOT_USERNAME, text)
    replies = await _wait_for_reply(app, after_message_id=sent.id, timeout=30.0)
    if not replies:
        print("(no reply within 30s)", flush=True)
        return
    for m in replies:
        _print_message(m)


async def cmd_click(app: Client, callback_data: str) -> None:
    """Find the most recent bot message with this callback_data button and click it."""
    chat = await app.get_chat(BOT_USERNAME)
    target_msg_id: int | None = None
    async for m in app.get_chat_history(BOT_USERNAME, limit=20):
        if m.reply_markup and hasattr(m.reply_markup, "inline_keyboard"):
            for row in m.reply_markup.inline_keyboard:
                for btn in row:
                    if getattr(btn, "callback_data", None) == callback_data:
                        target_msg_id = m.id
                        break
                if target_msg_id:
                    break
            if target_msg_id:
                break
    if not target_msg_id:
        print(f"(no recent button @{callback_data} found)", flush=True)
        return

    await app.request_callback_answer(chat.id, target_msg_id, callback_data, timeout=15)
    # Reply may be (a) an edit of the same message, (b) a new message, or both.
    after = target_msg_id  # start poll from this id, will pick up new edits/messages
    # Wait a bit for both edit + new message
    await asyncio.sleep(2.0)
    replies = await _wait_for_reply(app, after_message_id=after, timeout=15.0)
    # Also re-fetch the source message in case it was edited
    src = await app.get_messages(chat.id, target_msg_id)
    if src.edit_date:
        _print_message(src)
    for m in replies:
        _print_message(m)


async def cmd_last(app: Client, n: int = 3) -> None:
    """Show last N bot messages."""
    bot_id = (await app.get_users(BOT_USERNAME)).id
    items: list[Message] = []
    async for m in app.get_chat_history(BOT_USERNAME, limit=30):
        if m.from_user and m.from_user.id == bot_id:
            items.append(m)
            if len(items) >= n:
                break
    for m in reversed(items):
        _print_message(m)


async def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else ""

    session_string = _load_session()
    app = Client(
        "eventai_tester_runtime",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True,
    )
    await app.start()
    try:
        if cmd == "send":
            await cmd_send(app, arg)
        elif cmd == "click":
            await cmd_click(app, arg)
        elif cmd == "last":
            await cmd_last(app, int(arg or "3"))
        else:
            print(f"unknown cmd: {cmd}", file=sys.stderr)
    finally:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
