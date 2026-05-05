"""Router: /start command with smart re-entry, role selection, shortcut.

Transitions:
- /start -> check deep link (expert) / check existing profile / check expert / fresh start
- role:guest:* / role:business -> onboard_nl_profile
- role:shortcut -> view_program (all projects, no profiling)
"""

import logging
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.program import program_keyboard, project_buttons_keyboard
from src.bot.keyboards.roles import role_keyboard
from src.bot.states import BotStates
from src.models.event import Event
from src.models.expert import Expert
from src.models.guest_profile import GuestProfile
from src.models.project import Project
from src.models.recommendation import Recommendation
from src.models.user import User
from src.services.expert import get_expert_by_invite

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: AsyncSession) -> None:
    """Smart re-entry: deep link, existing profile, expert, or fresh start."""
    tg_user_id = str(message.from_user.id)
    args = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""

    # Get or create user
    result = await db.execute(select(User).where(User.telegram_user_id == tg_user_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            telegram_user_id=tg_user_id,
            full_name=message.from_user.full_name or "User",
            username=message.from_user.username,
        )
        db.add(user)
        await db.flush()

    # Get active event
    event_result = await db.execute(
        select(Event).where(Event.is_active.is_(True)).limit(1)
    )
    event = event_result.scalar_one_or_none()
    if not event:
        await message.answer("Нет активных мероприятий.")
        return

    await state.update_data(user_id=str(user.id), event_id=str(event.id))

    # Expert deep link: /start expert_<code>
    if args.startswith("expert_"):
        await _handle_expert_link(message, state, db, user, event, args[7:])
        return

    # Check existing expert
    expert_result = await db.execute(select(Expert).where(Expert.user_id == user.id))
    expert = expert_result.scalar_one_or_none()
    if expert and expert.bot_started:
        await state.set_state(BotStates.expert_dashboard)
        await state.update_data(expert_id=str(expert.id))
        from src.bot.routers.expert import show_dashboard

        await show_dashboard(message, state, db)
        return

    # Check existing guest profile for this event
    profile_result = await db.execute(
        select(GuestProfile).where(
            GuestProfile.user_id == user.id,
            GuestProfile.event_id == event.id,
        )
    )
    profile = profile_result.scalars().first()
    if profile:
        await _return_to_program(message, state, db, profile, event)
        return

    # Fresh start
    await state.set_state(BotStates.choose_role)
    await message.answer(
        "Привет! Я AI-куратор Demo Day.\n\n"
        "Помогу найти интересные проекты и составить программу.\n\n"
        "Выберите роль:",
        reply_markup=role_keyboard(),
    )


async def _handle_expert_link(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    event: Event,
    invite_code: str,
) -> None:
    """Process expert deep link."""
    expert = await get_expert_by_invite(db, invite_code)
    if not expert:
        await message.answer("Приглашение недействительно. Обратитесь к организатору.")
        await state.set_state(BotStates.choose_role)
        await message.answer("Выберите роль:", reply_markup=role_keyboard())
        return

    if not expert.bot_started:
        expert.bot_started = True
        expert.user_id = user.id
        await db.flush()

    user.role_code = "expert"
    await db.flush()

    await state.set_state(BotStates.expert_dashboard)
    await state.update_data(expert_id=str(expert.id))

    from src.bot.routers.expert import show_dashboard

    await show_dashboard(message, state, db)


async def _return_to_program(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    profile: GuestProfile,
    event: Event,
) -> None:
    """Return existing user to their program."""
    recs_result = await db.execute(
        select(Recommendation)
        .where(Recommendation.guest_profile_id == profile.id)
        .order_by(Recommendation.rank)
    )
    recs = list(recs_result.scalars().all())

    await state.set_state(BotStates.view_program)
    await state.update_data(profile_id=str(profile.id))

    if recs:
        from src.bot.routers.program import format_program

        text, project_list = await format_program(recs, db)
        keyboard = project_buttons_keyboard(project_list) if project_list else program_keyboard()
        await message.answer(
            f"С возвращением!\n\n{text}",
            reply_markup=keyboard,
        )
    else:
        await message.answer(
            "Профиль найден, но рекомендации устарели. Используйте /rebuild."
        )


@router.callback_query(BotStates.choose_role, F.data.startswith("role:"))
async def role_chosen(callback: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    """Handle role selection callback."""
    await callback.answer()

    data_parts = callback.data.split(":")
    state_data = await state.get_data()
    user_id = state_data["user_id"]
    event_id = state_data["event_id"]

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one()

    # Shortcut: show all projects without profiling
    if data_parts[1] == "shortcut":
        await _handle_shortcut(callback, state, db, user, event_id)
        return

    # Expert: ask for invite code
    if data_parts[1] == "expert":
        await state.set_state(BotStates.expert_invite_entry)
        await callback.message.edit_text(
            "Введите код приглашения эксперта (выдаётся организатором):"
        )
        await callback.answer()
        return

    # Set role and subrole
    if data_parts[1] == "business":
        user.role_code = "business"
        # role:business or role:business:hr
        user.subrole = data_parts[2] if len(data_parts) > 2 else None
    else:
        user.role_code = "guest"
        user.subrole = data_parts[2] if len(data_parts) > 2 else "other"
    await db.flush()

    # Transition to NL profiling
    await state.set_state(BotStates.onboard_nl_profile)
    await state.update_data(nl_conversation=[], nl_turn=0)

    await callback.message.edit_text(
        "Расскажите о ваших интересах, и я подберу проекты."
    )


@router.message(BotStates.expert_invite_entry, F.text)
async def expert_invite_text(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
) -> None:
    """User typed an invite code after clicking 'Эксперт / жюри'."""
    code = (message.text or "").strip()
    if not code or code.startswith("/"):
        # Likely a command — let global_cmds router handle on next attempt;
        # do nothing here so the user sees no echo.
        await message.answer(
            "Введите код приглашения эксперта (или /reset чтобы выбрать другую роль)."
        )
        return

    expert = await get_expert_by_invite(db, code)
    if not expert:
        await message.answer(
            "Код не найден. Проверьте правильность или обратитесь к организатору."
        )
        return

    state_data = await state.get_data()
    user_id = state_data.get("user_id")
    if not user_id:
        await message.answer("Сессия повреждена. Используйте /start.")
        return

    user_result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = user_result.scalar_one()

    if not expert.bot_started:
        expert.bot_started = True
        expert.user_id = user.id
        await db.flush()

    user.role_code = "expert"
    await db.flush()

    await state.set_state(BotStates.expert_dashboard)
    await state.update_data(expert_id=str(expert.id))

    from src.bot.routers.expert import show_dashboard

    await message.answer(f"Добро пожаловать, {expert.name}.")
    await show_dashboard(message, state, db)


async def _handle_shortcut(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    event_id: str,
) -> None:
    """Show all projects without profiling.

    Creates a placeholder GuestProfile (so view_program text/agent handlers
    have something to attach to) and pseudo-Recommendations for the first
    20 projects so that callbacks @project:N work the same as in the
    personalised flow. Order is alphabetical by title for predictability.
    """
    from uuid import UUID

    user.role_code = "guest"
    await db.flush()

    projects_result = await db.execute(
        select(Project).where(Project.event_id == event_id).order_by(Project.title)
    )
    projects = list(projects_result.scalars().all())[:20]

    # Create or reuse a placeholder profile for this user/event
    existing = await db.execute(
        select(GuestProfile).where(
            GuestProfile.user_id == user.id,
            GuestProfile.event_id == UUID(event_id),
        )
    )
    profile = existing.scalar_one_or_none()
    if not profile:
        profile = GuestProfile(
            user_id=user.id,
            event_id=UUID(event_id),
            selected_tags=[],
            keywords=[],
            nl_summary="Просмотр всех проектов без профилирования.",
        )
        db.add(profile)
        await db.flush()
    else:
        # Wipe stale recs so we can rebuild as a flat 20-project list
        from sqlalchemy import delete
        await db.execute(
            delete(Recommendation).where(
                Recommendation.guest_profile_id == profile.id
            )
        )
        await db.flush()

    # Build pseudo-recommendations so @project:N callbacks resolve
    for i, p in enumerate(projects, 1):
        db.add(
            Recommendation(
                guest_profile_id=profile.id,
                project_id=p.id,
                relevance_score=0.0,
                category="must_visit" if i <= 8 else "if_time",
                rank=i,
            )
        )
    await db.flush()
    await state.update_data(profile_id=str(profile.id))
    await state.set_state(BotStates.view_program)

    lines = ["Все проекты Demo Day (первые 20):\n"]
    project_list: list[tuple[int, str]] = []
    for i, p in enumerate(projects, 1):
        lines.append(f"#{i} {p.title}")
        project_list.append((i, p.title))
    if len(projects) == 20:
        lines.append("\nНажмите кнопку проекта чтобы открыть детали.")
        lines.append("Для персональной подборки используйте /rebuild.")

    await callback.message.edit_text("\n".join(lines))
    await callback.message.answer(
        "Откройте проект:",
        reply_markup=project_buttons_keyboard(project_list),
    )
