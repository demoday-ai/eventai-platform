"""Global slash-command router. Registered FIRST in the dispatcher.

These commands work in ANY FSM state. Without this router, commands like
`/profile` get swallowed by `F.text` catch-all handlers in the active
state-router (e.g. profiling.py, program.py).

Commands:
- /start    -> handled by start.py:cmd_start (NOT here, has CommandStart filter)
- /reset    -> wipe FSM and run /start logic
- /profile  -> show profile if exists
- /rebuild  -> wipe profile + recommendations, restart profiling
- /support  -> enter support chat
- /help     -> short menu
"""

import logging
from uuid import UUID

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.states import BotStates
from src.models.guest_profile import GuestProfile
from src.models.recommendation import Recommendation

logger = logging.getLogger(__name__)
router = Router()


def _format_profile_text(profile: GuestProfile) -> str:
    parts: list[str] = ["Ваш профиль:"]
    if profile.selected_tags:
        parts.append(f"Интересы: {', '.join(profile.selected_tags)}")
    if profile.keywords:
        parts.append(f"Цели: {', '.join(profile.keywords)}")
    if profile.company:
        parts.append(f"Компания: {profile.company}")
    if profile.position:
        parts.append(f"Должность: {profile.position}")
    if profile.objective:
        parts.append(f"Цель: {profile.objective}")
    if profile.nl_summary:
        parts.append("")
        parts.append(profile.nl_summary)
    return "\n".join(parts)


@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext) -> None:
    """Hard reset: wipe FSM state and prompt /start."""
    await state.clear()
    await message.answer(
        "Сессия сброшена. Нажмите /start чтобы начать заново."
    )


@router.message(Command("profile"))
async def cmd_profile(
    message: Message, state: FSMContext, db: AsyncSession
) -> None:
    """Show user profile from any state. Requires existing profile."""
    state_data = await state.get_data()
    profile_id = state_data.get("profile_id")
    if not profile_id:
        await message.answer(
            "Профиль ещё не создан. Используйте /start, "
            "чтобы пройти онбординг."
        )
        return

    result = await db.execute(
        select(GuestProfile).where(GuestProfile.id == UUID(profile_id))
    )
    profile = result.scalar_one_or_none()
    if not profile:
        await message.answer("Профиль не найден. Используйте /start.")
        return

    await message.answer(_format_profile_text(profile))


@router.message(Command("rebuild"))
async def cmd_rebuild(
    message: Message, state: FSMContext, db: AsyncSession
) -> None:
    """Wipe profile + recommendations and restart NL profiling."""
    state_data = await state.get_data()
    profile_id = state_data.get("profile_id")

    if profile_id:
        await db.execute(
            delete(Recommendation).where(
                Recommendation.guest_profile_id == UUID(profile_id)
            )
        )
        await db.execute(
            delete(GuestProfile).where(GuestProfile.id == UUID(profile_id))
        )
        await db.flush()

    await state.update_data(
        nl_conversation=[],
        nl_turn=0,
        extracted_profile=None,
        program_chat=[],
        profile_id=None,
    )
    await state.set_state(BotStates.onboard_nl_profile)
    await message.answer(
        "Давайте пересоздадим профиль. Расскажите о ваших интересах."
    )


@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext) -> None:
    """Enter support chat from any state."""
    from src.bot.keyboards.program import support_back_keyboard

    await state.set_state(BotStates.support_chat)
    await message.answer(
        "Вы в режиме чата с организатором.\n"
        "Напишите свой вопрос, и мы передадим его организатору.\n"
        "Лимит: 3 сообщения за 5 минут.",
        reply_markup=support_back_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    """Short menu of available commands."""
    current = await state.get_state()
    base = (
        "Команды:\n"
        "/start - начать или перезапустить\n"
        "/profile - показать ваш профиль\n"
        "/rebuild - пересоздать профиль и рекомендации\n"
        "/support - связь с организатором\n"
        "/reset - полный сброс сессии\n"
    )
    if current == BotStates.view_program.state:
        base += (
            "\nВ свободном чате можно писать:\n"
            "- 'Покажи проект 3'\n"
            "- 'Сравни проекты 1 и 2'\n"
            "- 'Какие вопросы задать автору?'"
        )
    await message.answer(base)
