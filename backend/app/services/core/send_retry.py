"""Shared retry helper for Telegram bot message sending."""

import asyncio
import logging
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class MessageSender(Protocol):
    """Protocol for sending messages (decouples services from telegram.Bot).

    Return type is `Any` so the protocol accepts both aiogram.Bot.send_message
    (returns Message) and any test stub. Callers that need message_id should
    rely on the concrete aiogram.Bot type instead.
    """

    async def send_message(self, chat_id: int | str, text: str, **kwargs) -> Any: ...


async def send_with_retry(
    sender: MessageSender,
    chat_id: int | str,
    text: str,
    max_retries: int = 3,
    parse_mode: str | None = None,
    disable_web_page_preview: bool = False,
) -> tuple[bool, str | None]:
    """Send a Telegram message with exponential backoff retry.

    Returns (success, error_message).
    """
    for attempt in range(max_retries):
        try:
            await sender.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
            return True, None
        except Exception as e:
            error_msg = str(e)
            if attempt < max_retries - 1:
                delay = 2**attempt  # 1s, 2s, 4s
                logger.warning(
                    "Retry %d/%d sending to %s: %s (waiting %ds)",
                    attempt + 1,
                    max_retries,
                    chat_id,
                    error_msg,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Failed to send to %s after %d attempts: %s",
                    chat_id,
                    max_retries,
                    error_msg,
                )
                return False, error_msg[:500]
    return False, "Max retries exceeded"
