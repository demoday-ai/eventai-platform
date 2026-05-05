"""Fallback router - registered LAST in the dispatcher.

Catches messages and callbacks that no state-specific or global router
handled. Slash commands live in global_cmds.py.
"""

import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.states import BotStates

logger = logging.getLogger(__name__)
router = Router()


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
async def fallback_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Context-aware fallback for outdated/invalid callbacks.

    Instead of a hard "button is outdated, /start" alert, give the user a
    soft hint that points back to the screen they are most likely on.
    """
    current = await state.get_state()
    if current == BotStates.view_program.state:
        await callback.answer(
            "Эта кнопка из старого экрана. Нажмите /profile или напишите вопрос текстом.",
            show_alert=False,
        )
    elif current == BotStates.view_detail.state:
        await callback.answer(
            "Эта кнопка устарела. Вернитесь к программе через /profile.",
            show_alert=False,
        )
    elif current == BotStates.expert_dashboard.state:
        await callback.answer(
            "Эта кнопка устарела. Откройте дашборд эксперта заново через /start.",
            show_alert=False,
        )
    elif current is None:
        await callback.answer(
            "Сессия истекла. Нажмите /start чтобы начать заново.",
            show_alert=True,
        )
    else:
        await callback.answer(
            "Кнопка устарела. /start для перезапуска.",
            show_alert=False,
        )
