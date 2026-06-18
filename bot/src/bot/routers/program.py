"""Router: view_program state - main agent interaction.

Handles:
- User text -> PydanticAI agent run (timeout=15s)
- /profile command -> show profile
- /rebuild command -> reset to profiling
- /support command -> support chat
- cmd:if_time callback -> show if_time recommendations
- cmd:profile callback -> show profile
- Agent tool calls that transition state (show_project -> view_detail)
"""

import asyncio
import logging
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.agent import AgentDeps, create_agent
from src.core.config import settings
from src.core.sanitize import sanitize_text
from src.bot.keyboards.program import (
    nav_back_keyboard,
    program_keyboard,
    project_buttons_keyboard,
)
from src.bot.states import BotStates
from src.models.chat_message import ChatMessage
from src.models.event import Event
from src.models.guest_profile import GuestProfile
from src.models.project import Project
from src.models.recommendation import Recommendation
from src.models.schedule_slot import ScheduleSlot
from src.models.room import Room
from src.models.user import User
from src.services.platform_client import PlatformClient

logger = logging.getLogger(__name__)
router = Router()

# Chat history limit per user
MAX_CHAT_HISTORY = 20


# /profile, /rebuild, /support handlers moved to global_cmds.py so they
# work in any FSM state (not only view_program).


@router.callback_query(BotStates.view_program, F.data == "cmd:profile")
async def cb_profile(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession
) -> None:
    """Show profile via button."""
    await callback.answer()

    state_data = await state.get_data()
    profile_id = state_data.get("profile_id")
    if not profile_id:
        await callback.message.answer("Профиль не найден.")
        return

    result = await db.execute(
        select(GuestProfile).where(GuestProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        await callback.message.answer("Профиль не найден.")
        return

    await callback.message.answer(
        _format_profile_text(profile), reply_markup=nav_back_keyboard()
    )


@router.callback_query(BotStates.view_program, F.data == "cmd:back_to_program")
async def cb_back_to_program(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession
) -> None:
    """Return to program: short nav message, not the full text wall."""
    await callback.answer()

    state_data = await state.get_data()
    profile_id = state_data.get("profile_id")
    if not profile_id:
        await callback.message.answer("Программа не найдена. /start.")
        return

    recs_result = await db.execute(
        select(Recommendation)
        .where(
            Recommendation.guest_profile_id == UUID(profile_id),
            Recommendation.category == "must_visit",
        )
        .order_by(Recommendation.rank)
    )
    recs = list(recs_result.scalars().all())
    if not recs:
        await callback.message.answer("Программа пуста. Используйте /recommend.")
        return

    await send_program_nav(callback.message, recs, db)


@router.callback_query(BotStates.view_program, F.data == "cmd:show_program")
async def cb_show_program(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession
) -> None:
    """Show the FULL program text explicitly (button «Показать программу»)."""
    await callback.answer()

    state_data = await state.get_data()
    profile_id = state_data.get("profile_id")
    if not profile_id:
        await callback.message.answer("Программа не найдена. /start.")
        return

    recs_result = await db.execute(
        select(Recommendation)
        .where(
            Recommendation.guest_profile_id == UUID(profile_id),
            Recommendation.category == "must_visit",
        )
        .order_by(Recommendation.rank)
    )
    recs = list(recs_result.scalars().all())
    if not recs:
        await callback.message.answer("Программа пуста. Используйте /recommend.")
        return

    text, project_list = await format_program(recs, db)
    keyboard = (
        project_buttons_keyboard(project_list)
        if project_list
        else program_keyboard()
    )
    await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(BotStates.view_program, F.data == "cmd:if_time")
async def cb_if_time(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession
) -> None:
    """Show if_time recommendations."""
    await callback.answer()

    state_data = await state.get_data()
    profile_id = state_data.get("profile_id")
    if not profile_id:
        await callback.message.answer("Рекомендации не найдены.")
        return

    recs_result = await db.execute(
        select(Recommendation)
        .where(
            Recommendation.guest_profile_id == profile_id,
            Recommendation.category == "if_time",
        )
        .order_by(Recommendation.rank)
    )
    recs = list(recs_result.scalars().all())

    if not recs:
        await callback.message.answer("Нет дополнительных рекомендаций.")
        return

    text, _ = await format_program(recs, db, header="Если успеете:")
    await callback.message.answer(text, reply_markup=nav_back_keyboard())


@router.callback_query(BotStates.view_program, F.data.startswith("project:"))
async def cb_project_detail(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession
) -> None:
    """Open project detail by inline button."""
    await callback.answer()
    try:
        rank = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.message.answer("Неверный номер проекта.")
        return
    from src.bot.routers.detail import show_project_detail

    await show_project_detail(callback, state, db, rank)


@router.callback_query(
    StateFilter(BotStates.view_program, BotStates.view_detail),
    F.data == "cmd:export_pdf",
)
async def cb_export_pdf(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession
) -> None:
    """Export recommendations as PDF document."""
    await callback.answer("Генерирую PDF...")

    state_data = await state.get_data()
    profile_id = state_data.get("profile_id")
    user_id = state_data.get("user_id")

    if not profile_id:
        await callback.message.answer("Нет рекомендаций для экспорта.")
        return

    recs_result = await db.execute(
        select(Recommendation)
        .where(Recommendation.guest_profile_id == UUID(profile_id))
        .order_by(Recommendation.rank)
    )
    recs = list(recs_result.scalars().all())

    if not recs:
        await callback.message.answer("Нет рекомендаций для экспорта.")
        return

    project_ids = [r.project_id for r in recs]
    proj_result = await db.execute(
        select(Project).where(Project.id.in_(project_ids))
    )
    projects = list(proj_result.scalars().all())

    # Get user name
    user_name = "Участник"
    if user_id:
        user_result = await db.execute(select(User).where(User.id == UUID(user_id)))
        user = user_result.scalar_one_or_none()
        if user:
            user_name = user.full_name

    from src.services.pdf_export import generate_recommendations_pdf
    from aiogram.types import BufferedInputFile

    try:
        pdf_buf = await generate_recommendations_pdf(
            recs, projects, user_name=user_name, db=db
        )
        # Defensive: re-seek in case the buffer pointer drifted between
        # creation and read (BytesIO position may be at EOF after write).
        pdf_buf.seek(0)
        data = pdf_buf.read()
        if not data:
            logger.error("PDF generated but buffer is empty for user %s", user_id)
            await callback.message.answer(
                "Не удалось сгенерировать PDF. Попробуйте позже."
            )
            return
        doc = BufferedInputFile(data, filename="demo_day_program.pdf")
        await callback.message.answer_document(doc, caption="Ваша программа Demo Day")
        await callback.message.answer("PDF готов, отправлен выше.")
    except Exception as exc:
        logger.error("PDF export failed for user %s: %s", user_id, exc, exc_info=True)
        await callback.message.answer(
            "Не удалось сгенерировать PDF. Попробуйте позже или /support."
        )


def _wants_program(message: Message) -> bool:
    """True if the user asks to SEE their program (not edit it)."""
    t = (message.text or "").lower()
    return any(p in t for p in (
        "покажи программ", "показать программ", "покажи мою программ",
        "моя программа", "мою программу", "программу целиком", "программа целиком",
        "весь список проект", "что у меня в программ", "покажи список проект",
    ))


@router.message(BotStates.view_program, F.text, _wants_program)
async def show_program_text(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
) -> None:
    """Deterministic program display for 'покажи программу' — renders the stored
    program verbatim (same format + buttons as the buttons path), so the agent
    never paraphrases it into a different / inconsistent text."""
    state_data = await state.get_data()
    profile_id = state_data.get("profile_id")
    recs: list[Recommendation] = []
    if profile_id:
        recs = list(
            (
                await db.execute(
                    select(Recommendation)
                    .where(Recommendation.guest_profile_id == UUID(profile_id))
                    .order_by(Recommendation.rank)
                )
            ).scalars().all()
        )
    if not recs:
        await message.answer("Программа пуста. Опишите интересы или используйте /rebuild.")
        return
    text, project_list = await format_program(recs, db)
    keyboard = project_buttons_keyboard(project_list) if project_list else program_keyboard()
    await message.answer(text, reply_markup=keyboard)


@router.message(BotStates.view_program, F.text)
async def view_program_text(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    platform: PlatformClient,
) -> None:
    """Main agent interaction: user text -> PydanticAI agent -> response."""
    state_data = await state.get_data()
    user_id = state_data.get("user_id")
    event_id = state_data.get("event_id")
    profile_id = state_data.get("profile_id")

    if not user_id or not event_id:
        await message.answer("Сессия потеряна. Используйте /start.")
        return

    # Load dependencies
    user_result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = user_result.scalar_one_or_none()
    if not user:
        await message.answer("Пользователь не найден. Используйте /start.")
        return

    event_result = await db.execute(select(Event).where(Event.id == event_id))
    event = event_result.scalar_one_or_none()
    if not event:
        await message.answer("Мероприятие не найдено.")
        return

    profile = None
    if profile_id:
        result = await db.execute(
            select(GuestProfile).where(GuestProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()

    # Load recommendations
    recs: list[Recommendation] = []
    if profile:
        recs_result = await db.execute(
            select(Recommendation)
            .where(Recommendation.guest_profile_id == profile.id)
            .order_by(Recommendation.rank)
        )
        recs = list(recs_result.scalars().all())

    # Truncate long messages
    user_text = message.text or ""
    if len(user_text) > 2000:
        user_text = user_text[:2000]
        await message.answer("Сообщение обрезано до 2000 символов.")

    # Save user message to chat history
    safe_text = sanitize_text(user_text) or ""
    chat_msg = ChatMessage(
        user_id=UUID(user_id),
        event_id=UUID(event_id),
        role="user",
        content=safe_text,
    )
    db.add(chat_msg)
    await db.flush()

    # If an organizer took over this conversation, the AI stays silent —
    # the guest message is saved (above) and the organizer answers from the admin.
    from src.services.support import is_taken_over

    if await is_taken_over(db, UUID(user_id), UUID(event_id)):
        return

    # Build and run agent
    deps = AgentDeps(
        platform=platform,
        db=db,
        user=user,
        profile=profile,
        recommendations=recs,
        event=event,
        support_history=state_data.get("support_history"),
        current_project_rank=state_data.get("current_project_rank"),
        current_project_title=state_data.get("current_project_title"),
    )

    # Load chat history from state (before try block so it's always defined)
    program_chat: list[dict] = state_data.get("program_chat", [])
    program_chat.append({"role": "user", "content": message.text})

    agent_ok = False
    try:
        agent = create_agent(platform.platform_url, platform.token, platform.current_session_id)

        # Trim history
        if len(program_chat) > MAX_CHAT_HISTORY:
            program_chat = program_chat[-MAX_CHAT_HISTORY:]

        # Run agent with timeout
        agent_result = await asyncio.wait_for(
            agent.run(
                message.text,
                deps=deps,
                message_history=[
                    _to_pydantic_message(m) for m in program_chat[:-1]
                ] if len(program_chat) > 1 else None,
            ),
            timeout=settings.agent_timeout,
        )

        reply_text = agent_result.output
        if not reply_text:
            reply_text = "Не удалось получить ответ. Попробуйте переформулировать."
        agent_ok = True

    except asyncio.TimeoutError:
        reply_text = "Обработка занимает больше времени. Попробуйте еще раз."
        logger.warning("Agent timeout for user %s", user_id)
        # A tool may have flushed partway before the timeout — clear any
        # pending-rollback state so the assistant_msg save below doesn't crash.
        await _safe_rollback(db)
    except Exception as e:
        reply_text = "Произошла ошибка. Попробуйте еще раз или используйте кнопки."
        logger.error("Agent error for user %s: %s", user_id, e, exc_info=True)
        # A failed tool flush poisons the session; rollback so the raw
        # PendingRollbackError never leaks to the user on the next flush.
        await _safe_rollback(db)

    if agent_ok:
        # Persist the exchange to chat history only on success. A failed turn is
        # dropped from history (pop the user msg appended above) so a bad message
        # can't replay into message_history and make the next turns keep failing
        # ("Произошла ошибка" sticking for several turns).
        program_chat.append({"role": "assistant", "content": reply_text})
        if len(program_chat) > MAX_CHAT_HISTORY:
            program_chat = program_chat[-MAX_CHAT_HISTORY:]
        await state.update_data(program_chat=program_chat)
    else:
        if program_chat and program_chat[-1].get("role") == "user":
            program_chat.pop()
        await state.update_data(program_chat=program_chat)

    # Persist the last-shown project (show_project may have updated deps) so the
    # next turn and the questions:/contact: buttons know the active project.
    # Only on success, to avoid overwriting context on a timeout/error.
    if agent_ok and deps.current_project_rank is not None:
        upd: dict = {"current_project_rank": deps.current_project_rank}
        if deps.current_project_title is not None:
            upd["current_project_title"] = deps.current_project_title
        rec = next(
            (r for r in recs if r.rank == deps.current_project_rank), None
        )
        if rec:
            upd["current_project_id"] = str(rec.project_id)
        await state.update_data(**upd)

    # Save to DB. Wrapped defensively: if the session is somehow still poisoned,
    # the reply must still reach the user instead of crashing the handler.
    try:
        assistant_msg = ChatMessage(
            user_id=UUID(user_id),
            event_id=UUID(event_id),
            role="assistant",
            content=sanitize_text(reply_text) or reply_text,
        )
        db.add(assistant_msg)
        await db.flush()
    except Exception as e:
        logger.error("Failed to persist assistant message for user %s: %s", user_id, e)
        await _safe_rollback(db)

    # Send reply, split long messages
    await _safe_send(message, reply_text)

    # If a tool changed the program, render it DETERMINISTICALLY (correct 1..N
    # order + project buttons) instead of trusting the LLM's prose, which
    # reorders/mis-numbers the list. deps.recommendations is already reloaded.
    if agent_ok and getattr(deps, "program_changed", False) and deps.recommendations:
        try:
            text, project_list = await format_program(
                deps.recommendations, db, header="Обновлённая программа:"
            )
            keyboard = (
                project_buttons_keyboard(project_list)
                if project_list
                else program_keyboard()
            )
            await message.answer(text, reply_markup=keyboard)
        except Exception as e:
            logger.error("Deterministic program render failed for %s: %s", user_id, e)


def _to_pydantic_message(msg: dict):
    """Convert dict message to PydanticAI ModelMessage format."""
    from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

    if msg["role"] == "user":
        return ModelRequest(parts=[UserPromptPart(content=msg["content"])])
    return ModelResponse(parts=[TextPart(content=msg["content"])])


async def send_program_nav(
    message,
    recs: list[Recommendation],
    db: AsyncSession,
) -> None:
    """Short return-to-program message: one line + project buttons.

    Used by every "back to program" path (project card, support, profile nav)
    instead of re-sending the full program text wall each time. The full
    program is rendered only on generation and via the «Показать программу»
    button (cmd:show_program).
    """
    project_list: list[tuple[int, str]] = []
    for rec in sorted(recs, key=lambda r: r.rank):
        proj_result = await db.execute(
            select(Project.title).where(Project.id == rec.project_id)
        )
        title = proj_result.scalar_one_or_none()
        if title:
            project_list.append((rec.rank, title))

    from src.bot.keyboards.program import (
        program_keyboard,
        project_buttons_keyboard,
    )

    keyboard = (
        project_buttons_keyboard(project_list, include_show_program=True)
        if project_list
        else program_keyboard()
    )
    await message.answer("Вы в программе. Выберите проект:", reply_markup=keyboard)


async def format_program(
    recs: list[Recommendation],
    db: AsyncSession,
    header: str = "Ваша программа:",
) -> tuple[str, list[tuple[int, str]]]:
    """Format recommendations list with schedule info.

    Multi-line layout per project so long titles + room names don't wrap into
    a single inline blob. **Sorted chronologically** within each category
    (must-visit first by start time, then if-time by start time) so the user
    can walk the day end-to-end without jumping around the schedule.

    Returns (text, [(rank, title), ...]).
    """
    # Pre-load slots for chronological sort, in one query.
    slot_ids = [r.slot_id for r in recs if r.slot_id]
    slots_by_id: dict = {}
    if slot_ids:
        rows = await db.execute(
            select(ScheduleSlot, Room.name.label("room_name"))
            .join(Room, ScheduleSlot.room_id == Room.id)
            .where(ScheduleSlot.id.in_(slot_ids))
        )
        for row in rows.all():
            slots_by_id[row[0].id] = (row[0], row.room_name)

    def _sort_key(r: Recommendation):
        # Tuple: category bucket (0=must, 1=if_time), then start_time.
        # Recs without a slot fall to the end of their bucket but before none.
        bucket = 0 if r.category == "must_visit" else 1
        slot_tuple = slots_by_id.get(r.slot_id) if r.slot_id else None
        start = slot_tuple[0].start_time if slot_tuple else None
        # Use ISO max for missing time so they sort to bucket end.
        from datetime import datetime, timezone
        return (bucket, start or datetime.max.replace(tzinfo=timezone.utc))

    sorted_recs = sorted(recs, key=_sort_key)

    lines: list[str] = [header, ""]
    project_list: list[tuple[int, str]] = []
    last_day_date = None  # date → re-insert day header on change
    last_bucket: int | None = None
    DAY_NAMES = {0: "День 1", 1: "День 2", 2: "День 3"}

    # GLOBAL ordered list of unique dates across the whole program, so the SAME
    # calendar date always maps to the same "День N" in both must_visit and
    # if_time sections (previously numbered independently → 07.02 shown as both
    # "День 1" and "День 2").
    all_dates: list = []
    for r in sorted_recs:
        slot_tuple = slots_by_id.get(r.slot_id) if r.slot_id else None
        if slot_tuple:
            d = slot_tuple[0].start_time.date()
            if d not in all_dates:
                all_dates.append(d)
    all_dates.sort()

    for rec in sorted_recs:
        # Load project
        proj_result = await db.execute(
            select(Project).where(Project.id == rec.project_id)
        )
        project = proj_result.scalar_one_or_none()
        if not project:
            continue

        project_list.append((rec.rank, project.title))

        # Schedule slot (use the pre-loaded map populated above)
        time_block: str | None = None
        room_name: str | None = None
        slot = None
        if rec.slot_id and rec.slot_id in slots_by_id:
            slot, room_name = slots_by_id[rec.slot_id]
            time_str = slot.start_time.strftime("%H:%M")
            end_str = slot.end_time.strftime("%H:%M")
            time_block = f"{time_str}–{end_str}"

        bucket = 0 if rec.category == "must_visit" else 1

        # Section header on bucket change to if_time (independent of slot, so
        # no-slot optional projects still land under the section).
        if bucket == 1 and last_bucket != 1:
            lines.append("🟡 ЕСЛИ УСПЕЕТЕ")
            lines.append("")
            last_day_date = None  # force day re-header inside the new section
        last_bucket = bucket

        # Day header on date change (only for projects that have a slot).
        slot_date = slot.start_time.date() if slot else None
        if slot_date and slot_date != last_day_date:
            day_idx = all_dates.index(slot_date)
            day_label = DAY_NAMES.get(day_idx, f"День {day_idx + 1}")
            lines.append(f"📅 {day_label} ({slot_date.strftime('%d.%m')})")
            lines.append("")
            last_day_date = slot_date

        # Multi-line block: title (numbered, no '#'), then time/room, then the
        # one-line "почему именно тебе" reason (llm_summary) if present.
        lines.append(f"{rec.rank}. {project.title}")
        if time_block and room_name:
            lines.append(f"⏰ {time_block} · 📍 {room_name}")
        elif time_block:
            lines.append(f"⏰ {time_block}")
        elif room_name:
            lines.append(f"📍 {room_name}")
        else:
            lines.append("🕓 слот не назначен")

        reason = getattr(rec, "llm_summary", None)
        if reason:
            lines.append(f"💡 {reason}")

        tags = ", ".join(project.tags[:3]) if project.tags else ""
        if tags:
            lines.append(f"🏷 {tags}")
        lines.append("")  # spacer between projects

    return "\n".join(lines).rstrip() + "\n", project_list


def _format_profile_text(profile: GuestProfile) -> str:
    """Format guest profile for display."""
    parts = ["Ваш профиль:\n"]
    if profile.selected_tags:
        parts.append(f"Интересы: {', '.join(profile.selected_tags)}")
    if profile.keywords:
        parts.append(f"Ключевые слова: {', '.join(profile.keywords)}")
    if profile.nl_summary:
        parts.append(f"\n{profile.nl_summary}")
    if profile.company:
        parts.append(f"\nКомпания: {profile.company}")
    if profile.position:
        parts.append(f"Должность: {profile.position}")
    if profile.business_objectives:
        parts.append(f"Бизнес-цели: {', '.join(profile.business_objectives)}")
    return "\n".join(parts)


async def _safe_send(message: Message, text: str, **_kwargs) -> None:
    """Send LLM text with Telegram-safe formatting via entities."""
    from src.core.telegram_format import send_formatted
    await send_formatted(message, text)


async def _safe_rollback(db: AsyncSession) -> None:
    """Roll back a possibly-poisoned session; never raise from cleanup."""
    try:
        await db.rollback()
    except Exception as e:  # pragma: no cover - rollback failure is itself rare
        logger.error("Rollback failed: %s", e)
