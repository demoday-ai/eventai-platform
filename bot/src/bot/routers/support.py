"""Router: support_chat state - communication with event organizer.

ADR-001: guest support messages are written into the unified thread model
(support_threads/support_messages), which the web admin reads. The organizer
replies from the admin; the answer is delivered back via backend bot_messenger.

Handles:
- Confirmation message on entry
- Persist user messages into the support thread
- Rate limit: 3 msg/5min in support
- "Назад к программе" button -> view_program
"""

import logging
import time
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.program import program_keyboard, support_back_keyboard
from src.bot.states import BotStates
from src.models.recommendation import Recommendation

logger = logging.getLogger(__name__)
router = Router()

# Support-specific rate limit
SUPPORT_RATE_LIMIT = 3
SUPPORT_RATE_WINDOW = 300  # 5 minutes in seconds


@router.callback_query(BotStates.view_program, F.data == "support:start")
async def cb_support_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Enter support chat from program view."""
    await callback.answer()
    await state.set_state(BotStates.support_chat)
    await callback.message.answer(
        "Вы в режиме чата с организатором.\n"
        "Напишите свой вопрос, и мы передадим его организатору.\n"
        "Лимит: 3 сообщения за 5 минут.",
        reply_markup=support_back_keyboard(),
    )


@router.message(BotStates.support_chat, F.text)
async def support_text(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
) -> None:
    """Forward user message to organizer chat."""
    state_data = await state.get_data()
    user_id = state_data.get("user_id")
    event_id = state_data.get("event_id")

    if not user_id or not event_id:
        await message.answer("Сессия потеряна. Используйте /start.")
        return

    # Support-specific rate limit
    support_timestamps: list[float] = state_data.get("support_timestamps", [])
    now = time.time()

    # Remove expired timestamps
    support_timestamps = [
        ts for ts in support_timestamps if now - ts < SUPPORT_RATE_WINDOW
    ]

    if len(support_timestamps) >= SUPPORT_RATE_LIMIT:
        remaining = int(SUPPORT_RATE_WINDOW - (now - support_timestamps[0]))
        await message.answer(
            f"Лимит сообщений в поддержку ({SUPPORT_RATE_LIMIT}/5мин). "
            f"Подождите {remaining} сек.",
            reply_markup=support_back_keyboard(),
        )
        return

    support_timestamps.append(now)
    await state.update_data(support_timestamps=support_timestamps)

    # ADR-001: write into the unified thread model (support_threads/messages),
    # which the web admin reads. Organizer replies from the admin and the answer
    # is delivered back via backend bot_messenger.
    from src.services.support import add_user_support_message

    await add_user_support_message(db, UUID(user_id), UUID(event_id), message.text)

    await message.answer(
        "Сообщение отправлено организатору.\n"
        "Ответ придёт в этот чат.",
        reply_markup=support_back_keyboard(),
    )


@router.callback_query(BotStates.support_chat, F.data == "support:back")
async def cb_support_back(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession
) -> None:
    """Return from support to program view."""
    await callback.answer()

    # Save support history for agent context injection (ADR-001: from the thread)
    state_data = await state.get_data()
    user_id = state_data.get("user_id")
    event_id = state_data.get("event_id")
    if user_id and event_id:
        from src.services.support import get_support_history

        support_history = await get_support_history(
            db, UUID(user_id), UUID(event_id)
        )
        if support_history:
            await state.update_data(support_history=support_history)

    await state.set_state(BotStates.view_program)

    profile_id = state_data.get("profile_id")

    if profile_id:
        recs_result = await db.execute(
            select(Recommendation)
            .where(Recommendation.guest_profile_id == profile_id)
            .order_by(Recommendation.rank)
        )
        recs = list(recs_result.scalars().all())

        if recs:
            from src.bot.routers.program import send_program_nav

            await send_program_nav(callback.message, recs, db)
            return

    await callback.message.answer(
        "Назад к программе.", reply_markup=program_keyboard()
    )
