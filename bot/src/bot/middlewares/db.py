import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from src.core.database import async_session

logger = logging.getLogger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    """Inject AsyncSession into handler data; commit on success, rollback on error.

    On exception we roll back, log a full traceback for ourselves, and send the
    user a friendly message instead of letting raw asyncpg/SQLAlchemy errors
    surface in the chat. The exception is swallowed (not re-raised) so that
    follow-up callbacks in the same FSM session don't end up in
    "InFailedSQLTransactionError" cascades.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with async_session() as session:
            data["db"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception as exc:
                await session.rollback()
                logger.error("Handler failed: %s", exc, exc_info=True)
                try:
                    if isinstance(event, Message):
                        await event.answer(
                            "Что-то пошло не так. Попробуйте ещё раз или нажмите /start."
                        )
                    elif isinstance(event, CallbackQuery):
                        await event.answer(
                            "Ошибка. Нажмите /start чтобы начать заново.",
                            show_alert=True,
                        )
                except Exception:
                    # Don't mask the original error if we also fail to notify.
                    logger.exception("Failed to send user-facing error notice")
                return None
