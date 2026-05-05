"""Send-only aiogram.Bot singleton for backend (scheduler/messaging/support).

Background (031-bot-replacement):
The Telegram-side incoming long-poll lives in the standalone bot/ service.
Backend processes (FastAPI lifespan + APScheduler + Messaging/SupportChat APIs)
must NOT call getUpdates / start_polling — Telegram allows only one long-poll
per token. They use this module to send outbound messages through the same
token.

Usage:
    from app.services.core.bot_messenger import get_send_bot, close_send_bot

    bot = get_send_bot()
    await bot.send_message(chat_id=123, text="hello")

The aiogram.Bot instance is created lazily on first call and shared across
all callers. Call close_send_bot() in the FastAPI lifespan shutdown to
release the underlying aiohttp session.
"""

import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from app.config import settings

logger = logging.getLogger(__name__)


_bot: Bot | None = None


def get_send_bot() -> Bot:
    """Return the singleton send-only aiogram.Bot.

    Raises RuntimeError if BOT_TOKEN is not configured.
    """
    global _bot
    if _bot is None:
        if not settings.bot_token:
            raise RuntimeError("BOT_TOKEN is not set; cannot create aiogram.Bot")
        # parse_mode=None: callers either send plain text or pass parse_mode
        # explicitly per call. Avoids Markdown/MarkdownV2 surprises during
        # the PTB -> aiogram migration.
        _bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=None),
        )
        logger.info("Send-only aiogram.Bot initialised")
    return _bot


async def close_send_bot() -> None:
    """Close the singleton aiogram.Bot session. Idempotent."""
    global _bot
    if _bot is not None:
        try:
            await _bot.session.close()
        except Exception:
            logger.exception("Failed to close aiogram.Bot session")
        _bot = None
        logger.info("Send-only aiogram.Bot closed")
