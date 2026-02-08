"""Telegram bot utilities."""

import logging

from telegram import Bot, InlineKeyboardMarkup

from app.config import settings

logger = logging.getLogger(__name__)


def is_organizer(telegram_user_id: int | str) -> bool:
    """Check if user is an organizer."""
    return str(telegram_user_id) in settings.organizer_ids

MAX_TG_MESSAGE_LEN = 4096
SAFE_SPLIT_LEN = 4000  # Leave margin for formatting


async def safe_send_long_message(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = "Markdown",
) -> None:
    """Send a message, splitting into multiple parts if it exceeds Telegram's 4096 char limit.

    Splits on paragraph boundaries (double newline). The reply_markup keyboard
    is attached only to the last part.
    """
    if len(text) <= MAX_TG_MESSAGE_LEN:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        return

    parts = _split_text(text, SAFE_SPLIT_LEN)

    for i, part in enumerate(parts):
        is_last = i == len(parts) - 1
        await bot.send_message(
            chat_id=chat_id,
            text=part,
            reply_markup=reply_markup if is_last else None,
            parse_mode=parse_mode,
        )


def _split_text(text: str, max_len: int) -> list[str]:
    """Split text into chunks at paragraph boundaries, falling back to line/word boundaries."""
    if len(text) <= max_len:
        return [text]

    parts = []
    remaining = text

    while remaining:
        if len(remaining) <= max_len:
            parts.append(remaining)
            break

        chunk = remaining[:max_len]

        # Try paragraph boundary (double newline)
        split_pos = chunk.rfind("\n\n")
        if split_pos > max_len // 4:
            parts.append(remaining[:split_pos])
            remaining = remaining[split_pos + 2:]
            continue

        # Try single newline
        split_pos = chunk.rfind("\n")
        if split_pos > max_len // 4:
            parts.append(remaining[:split_pos])
            remaining = remaining[split_pos + 1:]
            continue

        # Try word boundary (space)
        split_pos = chunk.rfind(" ")
        if split_pos > max_len // 4:
            parts.append(remaining[:split_pos])
            remaining = remaining[split_pos + 1:]
            continue

        # Hard split as last resort
        parts.append(remaining[:max_len])
        remaining = remaining[max_len:]

    return [p for p in parts if p.strip()]
