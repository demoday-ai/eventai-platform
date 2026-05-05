"""Fallback router - registered LAST in the dispatcher.

Catches commands and messages that no state-specific router handled:
- /help in any state
- /support outside view_program
- /rebuild outside view_program
- Messages when FSM state is None (user hasn't run /start)
- Outdated/invalid callback queries
"""

import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)
router = Router()


# /help, /support, /rebuild moved to global_cmds.py (registered first in dispatcher).


@router.message()
async def fallback_no_state(message: Message, state: FSMContext) -> None:
    """Catch-all for messages without a matching handler.

    This covers users who send text before /start (state is None)
    and any other unhandled text in unexpected states.
    """
    current = await state.get_state()
    if current is None:
        await message.answer(
            "Привет! Используйте /start чтобы начать работу с ботом."
        )
    else:
        await message.answer(
            "Не удалось обработать сообщение. Попробуйте /start."
        )


@router.callback_query()
async def fallback_callback(callback: CallbackQuery) -> None:
    """Catch-all for outdated/invalid callback queries."""
    await callback.answer(
        "Кнопка устарела. Используйте /start.", show_alert=True
    )
