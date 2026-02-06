"""Unified onboarding + profiling ConversationHandler.

Flow for new users:
  /start → CHOOSE_ROLE → CHOOSE_SUBTYPE → ONBOARD_NL_PROFILE → ONBOARD_CONFIRM
                                                                    ↓
                                              [auto] _do_generate() → VIEW_PROGRAM

Flow for returning users with profile:
  /start → has role + profile? → YES → VIEW_PROGRAM (direct to agent mode)
                               → NO role → CHOOSE_ROLE (standard onboarding)

States (10 total):
  CHOOSE_ROLE → CHOOSE_SUBTYPE → ENTER_SUBTYPE → ONBOARD_NL_PROFILE → ONBOARD_CONFIRM
  → CONFIRM_CHANGE → VIEW_PROGRAM → VIEW_DETAIL → NL_REBUILD → NL_REBUILD_CONFIRM
"""

import logging
import uuid as _uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# NOTE: contact/follow-up features temporarily disabled
# from app.bot.handlers.contact import contact_button, contact_request_callback
from app.bot.keyboards import (
    check_readiness_keyboard,
    confirm_nl_profile_keyboard,
    guest_subtype_keyboard,
    nl_topic_buttons,
    program_recommendation_keyboard,
    resume_or_restart_keyboard,
    retry_generation_keyboard,
    role_keyboard,
)
from app.bot.utils import safe_send_long_message
from app.database import async_session
from app.models.role import RoleCode
from app.models.user import GUEST_SUBTYPE_DISPLAY, GuestSubtype
from app.services import (
    business_followup_service,
    followup_service,
    profiling_service,
    qa_service,
    user_service,
)

logger = logging.getLogger(__name__)

# Conversation states (10 total)
(
    CHOOSE_ROLE,          # 0 - Role selection
    CHOOSE_SUBTYPE,       # 1 - Guest subtype
    ENTER_SUBTYPE,        # 2 - Free text subtype
    ONBOARD_NL_PROFILE,   # 3 - NL profiling (onboarding)
    ONBOARD_CONFIRM,      # 4 - Profile confirmation (onboarding)
    CONFIRM_CHANGE,       # 5 - Role change (returning user)
    VIEW_PROGRAM,         # 6 - Agent mode (from profiling)
    VIEW_DETAIL,          # 7 - Project detail (from profiling)
    NL_REBUILD,           # 8 - Profile rebuild (from profiling)
    NL_REBUILD_CONFIRM,   # 9 - Rebuild confirmation (from profiling)
) = range(10)

# Fallback topic labels when DB is unavailable
_FALLBACK_TOPIC_LABELS: dict[str, str] = {
    "EdTech": "EdTech",
    "MedTech": "MedTech",
    "Wellness": "Wellness",
    "Agents": "Agents",
    "NLP": "NLP",
    "RAG": "RAG",
    "LLM": "LLM",
    "Retail": "Retail",
    "FinTech": "FinTech",
    "DevTools": "DevTools",
    "Analytics": "Analytics",
    "Media": "Media",
    "CV": "CV",
    "HR": "HR",
    "Security": "Security",
    "Industrial": "Industrial",
}


async def _get_topics() -> list[tuple[str, str]]:
    """Fetch topic tags from DB, falling back to _FALLBACK_TOPIC_LABELS."""
    try:
        from app.services import project_service
        async with async_session() as session:
            return await project_service.get_topic_tags_for_buttons(session)
    except Exception:
        logger.debug("_get_topics: DB unavailable, using fallback")
        return list(_FALLBACK_TOPIC_LABELS.items())

MAX_MESSAGE_LEN = 4096


# =============================================================================
# Helpers (from guest_profiling.py)
# =============================================================================


async def _check_guest_or_business(telegram_user_id: str) -> tuple | None:
    """Check if user has guest or business role. Returns (user, event, role_code) or None."""
    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(session, telegram_user_id)
        if not user:
            return None
        event = await user_service.get_current_event(session)
        if not event:
            return None
        role_info = await user_service.get_user_role_with_info(session, user.id, event.id)
        if not role_info or role_info.code not in (RoleCode.GUEST.value, RoleCode.BUSINESS.value):
            return None
        return user, event, role_info.code


def _truncate(text: str, limit: int) -> str:
    """Truncate text at sentence boundary, fallback to word boundary."""
    if not text or len(text) <= limit:
        return text
    chunk = text[:limit]
    for sep in (". ", "! ", "? ", ".\n"):
        pos = chunk.rfind(sep)
        if pos > limit // 3:
            return chunk[: pos + 1]
    pos = chunk.rfind(" ")
    if pos > limit // 3:
        return chunk[:pos] + "..."
    return chunk + "..."


def _escape_markdown(text: str) -> str:
    """Escape Markdown special characters (idempotent — won't double-escape)."""
    if not text:
        return ""
    for char in ['*', '_', '`', '[', ']', '(', ')']:
        # Remove existing escapes first, then re-escape uniformly
        text = text.replace('\\' + char, char)
        text = text.replace(char, '\\' + char)
    return text


def _format_recommendations(data: dict) -> list[str]:
    """Format must-visit recommendations into message parts (respecting 4096 char limit)."""
    messages = []

    must_text = "*Топ-рекомендации:*\n\n"
    for rec in data.get("must_visit", []):
        title = _escape_markdown(rec["title"])
        summary = _escape_markdown(_truncate(rec["summary"], 150) if rec["summary"] else "")
        room_info = f"Зал {rec['room_number']}" if rec.get("room_number") else ""
        tags_str = ", ".join(rec.get("tags", [])[:3])
        conflict = ""
        if rec.get("conflict_rooms"):
            conflict = f" (пересекается с залом {', '.join(str(r) for r in rec['conflict_rooms'][:2])})"

        score = int(rec.get("relevance_score", 0))
        entry = (
            f"*{rec['rank']}. {title}* — {score}%\n"
            f"{summary}\n"
            f"{room_info} · {tags_str}{conflict}\n\n"
        )
        must_text += entry

    if len(must_text) > MAX_MESSAGE_LEN:
        must_recs = data.get("must_visit", [])
        mid = len(must_recs) // 2
        part1 = "*Топ-рекомендации:*\n\n"
        part2 = ""
        for i, rec in enumerate(must_recs):
            title = _escape_markdown(rec["title"])
            summary = _escape_markdown(_truncate(rec["summary"], 150) if rec["summary"] else "")
            room_info = f"Зал {rec['room_number']}" if rec.get("room_number") else ""
            tags_str = ", ".join(rec.get("tags", [])[:3])
            conflict = ""
            if rec.get("conflict_rooms"):
                conflict = f" (пересекается с залом {', '.join(str(r) for r in rec['conflict_rooms'][:2])})"
            entry = (
                f"*{rec['rank']}. {title}*\n"
                f"{summary}\n"
                f"{room_info} · {tags_str}{conflict}\n\n"
            )
            if i < mid:
                part1 += entry
            else:
                part2 += entry
        messages.append(part1)
        if part2:
            messages.append(part2)
    else:
        messages.append(must_text)

    return messages


def _format_if_time(data: dict) -> list[str]:
    """Format if-time recommendations into message parts."""
    messages = []
    if_time_text = "*Дополнительно:*\n\n"
    for rec in data.get("if_time", []):
        title = _escape_markdown(rec["title"])
        summary = _escape_markdown(_truncate(rec["summary"], 150) if rec["summary"] else "")
        room_info = f"Зал {rec['room_number']}" if rec.get("room_number") else ""
        tags_str = ", ".join(rec.get("tags", [])[:3])

        score = int(rec.get("relevance_score", 0))
        entry = (
            f"*{rec['rank']}. {title}* — {score}%\n"
            f"{summary}\n"
            f"{room_info} · {tags_str}\n\n"
        )
        if_time_text += entry

    if len(if_time_text) > MAX_MESSAGE_LEN:
        if_recs = data.get("if_time", [])
        mid = len(if_recs) // 2
        part1 = "*Дополнительно:*\n\n"
        part2 = ""
        for i, rec in enumerate(if_recs):
            title = _escape_markdown(rec["title"])
            summary = _escape_markdown(_truncate(rec["summary"], 150) if rec["summary"] else "")
            room_info = f"Зал {rec['room_number']}" if rec.get("room_number") else ""
            tags_str = ", ".join(rec.get("tags", [])[:3])
            entry = (
                f"*{rec['rank']}. {title}*\n"
                f"{summary}\n"
                f"{room_info} · {tags_str}\n\n"
            )
            if i < mid:
                part1 += entry
            else:
                part2 += entry
        messages.append(part1)
        if part2:
            messages.append(part2)
    else:
        messages.append(if_time_text)

    return messages


# =============================================================================
# Entry point: /start command
# =============================================================================


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command — entry point for onboarding."""
    # Check if this is an expert deep link: /start expert
    if context.args and context.args[0] == "expert":
        from app.bot.handlers.expert_assignment import handle_expert_start
        return await handle_expert_start(update, context)

    # Fix 11: Check if user has active profiling session
    nl_conversation = context.user_data.get("nl_conversation", [])
    if nl_conversation:
        await update.message.reply_text(
            "Вы уже начали подбор программы. Продолжить или начать заново?",
            reply_markup=resume_or_restart_keyboard(),
        )
        return CONFIRM_CHANGE

    tg_user = update.effective_user
    telegram_user_id = str(tg_user.id)
    full_name = tg_user.full_name or tg_user.first_name
    username = tg_user.username

    async with async_session() as session:
        user = await user_service.upsert_user(
            session, telegram_user_id, full_name, username
        )

        event = await user_service.get_current_event(session)
        if not event:
            await update.message.reply_text(
                "Сейчас нет запланированных мероприятий.\n\n"
                "Мы пришлём уведомление, когда откроется регистрация "
                "на ближайший Demo Day."
            )
            return ConversationHandler.END

        role = await user_service.get_user_role_with_info(session, user.id, event.id)

        # Check if user has profile with selected tags (returning user)
        profile = None
        has_profile = False
        if role and role.code in (RoleCode.GUEST.value, RoleCode.BUSINESS.value):
            profile = await profiling_service.get_or_create_profile(session, user.id, event.id)
            has_profile = bool(profile.selected_tags)

    logger.info(
        "start: user=%s tg_id=%s has_role=%s has_profile=%s",
        full_name,
        telegram_user_id,
        role is not None,
        has_profile,
    )

    # Returning user with profile → direct to agent mode
    if role and has_profile and profile:
        context.user_data["profile_id"] = str(profile.id)
        context.user_data["profile_user_id"] = str(user.id)
        context.user_data["profile_event_id"] = str(event.id)

        await update.message.reply_text(
            f"С возвращением, {full_name}! Загружаю вашу программу..."
        )
        return await _do_generate_from_message(update, context)

    # Returning user with role but no profile → continue profiling directly
    if role and not has_profile:
        context.user_data["pending_role_code"] = role.code
        context.user_data["event_id"] = str(event.id)
        context.user_data["nl_topics"] = set()
        context.user_data["nl_conversation"] = []
        if profile:
            context.user_data["profile_id"] = str(profile.id)
            context.user_data["profile_user_id"] = str(user.id)
            context.user_data["profile_event_id"] = str(event.id)
        await update.message.reply_text(
            f"С возвращением, {full_name}! Давайте продолжим подбор программы.\n\n"
            f"Расскажите, что вас интересует на Demo Day?\n"
            f"Напишите свободным текстом или выберите темы кнопками:",
            reply_markup=nl_topic_buttons(prefix="onb_nl", topics=await _get_topics()),
        )
        return ONBOARD_NL_PROFILE

    # New user → start onboarding
    context.user_data["event_id"] = str(event.id)
    context.user_data["nl_topics"] = set()
    context.user_data["nl_conversation"] = []

    await update.message.reply_text(
        f"Добро пожаловать на Demo Day, {full_name}!\n\n"
        f"Кто вы?",
        reply_markup=role_keyboard(),
    )
    return CHOOSE_ROLE


# =============================================================================
# CHOOSE_ROLE state
# =============================================================================


async def role_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle role selection: Guest → subtype selection, Partner → NL profiling."""
    query = update.callback_query
    await query.answer()

    _, role_code_str = query.data.split(":", 1)
    role_code = RoleCode(role_code_str)

    tg_user = query.from_user
    telegram_user_id = str(tg_user.id)

    context.user_data["pending_role_code"] = role_code.value
    context.user_data["nl_topics"] = set()
    context.user_data["nl_conversation"] = []

    if role_code == RoleCode.GUEST:
        # Guest → choose subtype
        await query.edit_message_text(
            "Уточните, кто вы:",
            reply_markup=guest_subtype_keyboard(),
        )
        return CHOOSE_SUBTYPE

    # Partner → assign role immediately, then NL profiling
    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(session, telegram_user_id)
        event = await user_service.get_current_event(session)
        role = await user_service.get_role_by_code(session, role_code)

        if not role or not event or not user:
            await query.edit_message_text("Ошибка. Попробуйте /start заново.")
            return ConversationHandler.END

        await user_service.set_role(session, user.id, event.id, role)

    logger.info("role_chosen: tg_id=%s role=%s", telegram_user_id, role_code.value)

    await query.edit_message_text(
        "Отлично! Задам пару вопросов, чтобы подобрать проекты для вас — "
        "это займёт буквально пару минут.\n\n"
        "Расскажите, что вас интересует на Demo Day?\n"
        "Напишите свободным текстом или выберите темы кнопками:",
        reply_markup=nl_topic_buttons(prefix="onb_nl", topics=await _get_topics()),
    )
    return ONBOARD_NL_PROFILE


# =============================================================================
# CHOOSE_SUBTYPE state
# =============================================================================


async def subtype_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle guest subtype selection."""
    query = update.callback_query
    await query.answer()

    _, subtype_str = query.data.split(":", 1)
    guest_subtype = GuestSubtype(subtype_str)

    tg_user = query.from_user
    telegram_user_id = str(tg_user.id)

    context.user_data["guest_subtype"] = guest_subtype.value

    if guest_subtype == GuestSubtype.OTHER:
        # "Другое" → ask for free text subtype
        await query.edit_message_text(
            "Напишите, кто вы (например: «преподаватель», «журналист», «HR»):"
        )
        return ENTER_SUBTYPE

    # Assign role with subtype, then go to NL profiling
    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(session, telegram_user_id)
        event = await user_service.get_current_event(session)
        role = await user_service.get_role_by_code(session, RoleCode.GUEST)

        if not role or not event or not user:
            await query.edit_message_text("Ошибка. Попробуйте /start заново.")
            return ConversationHandler.END

        await user_service.set_role(
            session, user.id, event.id, role, guest_subtype=guest_subtype
        )

    subtype_name = GUEST_SUBTYPE_DISPLAY.get(guest_subtype, subtype_str)
    logger.info("subtype_chosen: tg_id=%s subtype=%s", telegram_user_id, subtype_str)

    await query.edit_message_text(
        f"Отлично, {subtype_name}! Задам пару вопросов, чтобы подобрать "
        f"проекты под тебя — это займёт буквально пару минут.\n\n"
        f"Расскажи, что тебе интересно на Demo Day?\n"
        f"Напиши свободным текстом или выбери темы кнопками:",
        reply_markup=nl_topic_buttons(prefix="onb_nl", topics=await _get_topics()),
    )
    return ONBOARD_NL_PROFILE


# =============================================================================
# ENTER_SUBTYPE state (free text for "Другое")
# =============================================================================


async def enter_subtype_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle free text entry for custom guest subtype."""
    custom_subtype = update.message.text.strip()
    tg_user = update.effective_user
    telegram_user_id = str(tg_user.id)

    # Save as OTHER subtype, store custom text in user_data
    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(session, telegram_user_id)
        event = await user_service.get_current_event(session)
        role = await user_service.get_role_by_code(session, RoleCode.GUEST)

        if not role or not event or not user:
            await update.message.reply_text("Ошибка. Попробуйте /start заново.")
            return ConversationHandler.END

        await user_service.set_role(
            session, user.id, event.id, role, guest_subtype=GuestSubtype.OTHER
        )

    context.user_data["custom_subtype"] = custom_subtype
    logger.info("enter_subtype: tg_id=%s custom=%s", telegram_user_id, custom_subtype)

    await update.message.reply_text(
        f"Понятно, {custom_subtype}! Задам пару вопросов, чтобы подобрать "
        f"проекты под вас — это займёт буквально пару минут.\n\n"
        f"Расскажите, что вас интересует на Demo Day?\n"
        f"Напишите свободным текстом или выберите темы кнопками:",
        reply_markup=nl_topic_buttons(prefix="onb_nl", topics=await _get_topics()),
    )
    return ONBOARD_NL_PROFILE


# =============================================================================
# ONBOARD_NL_PROFILE state (NL profiling during onboarding)
# =============================================================================


def _get_conversation(context: ContextTypes.DEFAULT_TYPE) -> list[dict]:
    """Get conversation history from user_data."""
    return context.user_data.get("nl_conversation", [])


def _add_to_conversation(
    context: ContextTypes.DEFAULT_TYPE, role: str, content: str
) -> list[dict]:
    """Append a message to conversation history and return it."""
    conv = context.user_data.get("nl_conversation", [])
    conv.append({"role": role, "content": content})
    context.user_data["nl_conversation"] = conv
    return conv


async def _onb_nl_topic_buttons_with_selection(selected: set[str]):
    """Rebuild NL topic buttons with checkmarks for selected topics (onboarding)."""
    topics = await _get_topics()
    buttons = []
    row = []
    for tag_key, display in topics:
        prefix = "✓ " if tag_key in selected else ""
        row.append(InlineKeyboardButton(
            f"{prefix}{display}", callback_data=f"onb_nl:topic:{tag_key}",
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Готово →", callback_data="onb_nl:done")])
    return InlineKeyboardMarkup(buttons)


async def onb_nl_topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle topic button toggles and 'done' in onboarding NL profiling."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "onb_nl:done":
        # User pressed "Готово" with selected topics — inject as user message
        topics = context.user_data.get("nl_topics", set())
        if not topics and not _get_conversation(context):
            await query.edit_message_text(
                "Укажите хотя бы одну тему или напишите текстом, что вас интересует.",
                reply_markup=nl_topic_buttons(prefix="onb_nl", topics=await _get_topics()),
            )
            return ONBOARD_NL_PROFILE

        if topics:
            display_labels = [_FALLBACK_TOPIC_LABELS.get(t, t) for t in topics]
            topic_msg = f"Меня интересуют темы: {', '.join(display_labels)}"
            conv = _add_to_conversation(context, "user", topic_msg)
        else:
            conv = _get_conversation(context)

        return await _onb_agent_turn(update, context, conv)

    # Toggle topic
    _, _, topic_key = data.split(":", 2)
    topics = context.user_data.get("nl_topics", set())
    if topic_key in topics:
        topics.discard(topic_key)
    else:
        topics.add(topic_key)
    context.user_data["nl_topics"] = topics

    # Rebuild keyboard with checkmarks
    await query.edit_message_reply_markup(
        reply_markup=await _onb_nl_topic_buttons_with_selection(topics)
    )
    return ONBOARD_NL_PROFILE


async def onb_nl_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle free text input in onboarding NL profiling — conversational agent."""
    user_text = update.message.text
    conv = _add_to_conversation(context, "user", user_text)
    return await _onb_agent_turn(update, context, conv, is_message=True)


async def _onb_agent_turn(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    conversation: list[dict],
    is_message: bool = False,
) -> int:
    """Send conversation to LLM agent, handle reply or profile extraction."""
    from app.worker.tasks import chat_for_profile_task
    from app.worker.utils import wait_for_task

    selected_tags = list(context.user_data.get("nl_topics", set()))
    role_code = context.user_data.get("pending_role_code")
    guest_subtype = context.user_data.get("guest_subtype")
    custom_subtype = context.user_data.get("custom_subtype")

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    # Submit to Celery
    task = chat_for_profile_task.delay(
        conversation, selected_tags,
        role_code=role_code,
        guest_subtype=guest_subtype,
        custom_subtype=custom_subtype,
    )

    # Wait for result (short timeout for chat)
    completed, result = await wait_for_task(task.id, timeout=15, poll_interval=0.5)

    if not completed or result is None:
        # Fallback response
        result = {"action": "reply", "message": "Расскажите подробнее о ваших интересах."}

    if result["action"] == "profile":
        # Enforce at least one question before profile confirmation
        user_messages = [m for m in conversation if m.get("role") == "user"]
        assistant_messages = [m for m in conversation if m.get("role") == "assistant"]
        if len(user_messages) <= 1 and len(assistant_messages) == 0:
            # First turn - force a follow-up question instead of immediate profile
            fallback_question = "Отлично! А какую задачу ты хочешь решить или что хочешь узнать на Demo Day?"
            _add_to_conversation(context, "assistant", fallback_question)
            if not is_message:
                await update.callback_query.edit_message_reply_markup(reply_markup=None)
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=fallback_question,
            )
            return ONBOARD_NL_PROFILE

        # Agent decided we have enough info — show confirmation
        context.user_data["extracted_profile"] = result
        return await _show_onb_profile_confirmation(update, context, result, is_message)

    # Agent wants to continue the conversation
    reply_text = result["message"]
    _add_to_conversation(context, "assistant", reply_text)

    if not is_message:
        await update.callback_query.edit_message_reply_markup(reply_markup=None)
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=reply_text,
    )

    return ONBOARD_NL_PROFILE


async def _show_onb_profile_confirmation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    profile_data: dict,
    is_message: bool = False,
) -> int:
    """Show extracted profile for user confirmation (onboarding)."""
    summary = profile_data.get("summary", "")
    interests = profile_data.get("interests", [])
    goals = profile_data.get("goals", [])

    # Merge button-picked topics + LLM-extracted interests for display
    button_tags = list(context.user_data.get("nl_topics", set()))
    all_tags = list(dict.fromkeys(button_tags + interests))

    confirm_parts = []

    # Partner-specific fields
    company = profile_data.get("company")
    position = profile_data.get("position")
    if company or position:
        biz_line = []
        if company:
            biz_line.append(f"Компания: {company}")
        if position:
            biz_line.append(f"Должность: {position}")
        confirm_parts.append("\n".join(biz_line))

    partner_status = profile_data.get("partner_status")
    if partner_status:
        status_label = "текущий партнёр" if partner_status == "current" else "потенциальный партнёр"
        confirm_parts.append(f"Статус: {status_label}")

    business_objectives = profile_data.get("business_objectives")
    if business_objectives:
        obj_labels = {
            "technology": "технологии",
            "hiring": "найм",
            "investment": "инвестиции",
            "partnership": "партнёрство",
        }
        obj_display = [obj_labels.get(o, o) for o in business_objectives]
        confirm_parts.append(f"Бизнес-цели: {', '.join(obj_display)}")

    if summary:
        confirm_parts.append(summary)
    if all_tags:
        confirm_parts.append(f"Теги: {', '.join(all_tags)}")
    if goals:
        confirm_parts.append(f"Цели: {', '.join(goals)}")

    if not confirm_parts:
        confirm_parts.append("Общий интерес к Demo Day")

    confirm_text = "Ваш профиль:\n\n" + "\n".join(confirm_parts) + "\n\nВсё верно?"

    if not is_message:
        await update.callback_query.edit_message_reply_markup(reply_markup=None)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=confirm_text,
        reply_markup=confirm_nl_profile_keyboard(prefix="onb_nlconf"),
    )

    return ONBOARD_CONFIRM


# =============================================================================
# ONBOARD_CONFIRM state (profile confirmation during onboarding)
# =============================================================================


async def onb_confirm_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle profile confirmation: yes → save & generate program, retry → back to NL."""
    query = update.callback_query
    await query.answer()

    _, choice = query.data.split(":", 1)

    if choice == "retry":
        context.user_data["nl_topics"] = set()
        context.user_data["nl_conversation"] = []
        await query.edit_message_text(
            "Давайте попробуем заново.\n\n"
            "Расскажите, что вас интересует на Demo Day?\n"
            "Напишите свободным текстом или выберите темы кнопками:",
            reply_markup=nl_topic_buttons(prefix="onb_nl", topics=await _get_topics()),
        )
        return ONBOARD_NL_PROFILE

    # choice == "yes" — save profile and generate program
    tg_user = query.from_user
    telegram_user_id = str(tg_user.id)
    profile_data = context.user_data.get("extracted_profile", {})
    interests = profile_data.get("interests", [])
    # nl_topics stores DB tag names directly (e.g. "NLP", "CV")
    button_tags = list(context.user_data.get("nl_topics", set()))

    # Build raw_text from full conversation history
    conversation = context.user_data.get("nl_conversation", [])
    raw_text = "\n".join(
        f"{'Гость' if m['role'] == 'user' else 'Куратор'}: {m['content']}"
        for m in conversation
    )

    # All confirmed tags: button picks + LLM-extracted interests (deduplicated)
    all_tags = list(dict.fromkeys(button_tags + interests))

    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(session, telegram_user_id)
        event = await user_service.get_current_event(session)

        if not user or not event:
            await query.edit_message_text("Ошибка. Попробуйте /start заново.")
            return ConversationHandler.END

        # Build extra_data: always include nl_summary, plus business fields if present
        extra_data = {}
        summary = profile_data.get("summary")
        if summary:
            extra_data["nl_summary"] = summary
        for k in ("company", "position", "partner_status", "business_objectives"):
            if k in profile_data:
                extra_data[k] = profile_data[k]
        if not extra_data:
            extra_data = None

        profile = await profiling_service.get_or_create_profile(
            session, user.id, event.id
        )
        await profiling_service.save_profile(
            session,
            profile,
            selected_tags=all_tags,
            keywords=profile_data.get("goals", []),
            raw_text=raw_text or None,
            extra_data=extra_data,
        )

        # Store profile info for generation
        context.user_data["profile_id"] = str(profile.id)
        context.user_data["profile_user_id"] = str(user.id)
        context.user_data["profile_event_id"] = str(event.id)

    logger.info("Profile confirmed via NL: tg_id=%s tags=%s", telegram_user_id, all_tags)

    # Generate program immediately
    await query.edit_message_text("Профиль сохранён! Генерирую программу... ⏳")

    return await _do_generate(update, context)


# =============================================================================
# CONFIRM_CHANGE state (returning user)
# =============================================================================


async def confirm_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    data = query.data

    # Handle resume/restart from Fix 11 (profiling in progress)
    if data == "prof:resume":
        await query.edit_message_text(
            "Продолжаем! Расскажите, что вас интересует, "
            "или выберите темы кнопками:",
            reply_markup=nl_topic_buttons(prefix="onb_nl", topics=await _get_topics()),
        )
        return ONBOARD_NL_PROFILE

    if data == "prof:restart":
        context.user_data["nl_topics"] = set()
        context.user_data["nl_conversation"] = []
        context.user_data.pop("recommendations", None)
        context.user_data.pop("program_chat", None)

    _, choice = data.split(":", 1)

    if choice == "no":
        await query.edit_message_text("Хорошо, роль не изменена.")
        return ConversationHandler.END

    context.user_data["nl_topics"] = set()
    context.user_data["nl_conversation"] = []
    await query.edit_message_text(
        "Выберите новую роль:",
        reply_markup=role_keyboard(),
    )
    return CHOOSE_ROLE


# =============================================================================
# VIEW_PROGRAM state (agent mode)
# =============================================================================


async def _do_generate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Run recommendation generation and display results (from callback)."""
    from app.worker.tasks import generate_recommendations_task
    from app.worker.utils import wait_for_task

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    user_id = context.user_data["profile_user_id"]
    event_id = context.user_data["profile_event_id"]

    # Submit task to Celery
    task = generate_recommendations_task.delay(user_id, event_id)
    logger.info("Submitted generate_recommendations_task: task_id=%s", task.id)

    # Wait for result with timeout (30s for recommendation generation)
    completed, data = await wait_for_task(task.id, timeout=40, poll_interval=1.0)

    if not completed:
        # Task still running - save task_id for later polling
        context.user_data["pending_task_id"] = task.id
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Генерация программы занимает больше времени, чем обычно. "
                 "Нажмите кнопку ниже, чтобы проверить готовность.",
            reply_markup=check_readiness_keyboard(),
        )
        return VIEW_PROGRAM

    if not data or data.get("total", 0) == 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Не удалось найти подходящие проекты. Попробуйте обновить профиль через /start.",
        )
        return ConversationHandler.END

    context.user_data["recommendations"] = data
    context.user_data.pop("pending_task_id", None)
    return await _show_program(update, context)


async def _do_generate_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Run recommendation generation and display results (from message)."""
    from app.worker.tasks import generate_recommendations_task
    from app.worker.utils import wait_for_task

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    user_id = context.user_data["profile_user_id"]
    event_id = context.user_data["profile_event_id"]

    # Submit task to Celery
    task = generate_recommendations_task.delay(user_id, event_id)
    logger.info("Submitted generate_recommendations_task: task_id=%s", task.id)

    # Wait for result with timeout (30s for recommendation generation)
    completed, data = await wait_for_task(task.id, timeout=40, poll_interval=1.0)

    if not completed:
        # Task still running - save task_id for later polling
        context.user_data["pending_task_id"] = task.id
        await update.message.reply_text(
            "Генерация программы занимает больше времени, чем обычно. "
            "Нажмите кнопку ниже, чтобы проверить готовность.",
            reply_markup=check_readiness_keyboard(),
        )
        return VIEW_PROGRAM

    if not data or data.get("total", 0) == 0:
        await update.message.reply_text(
            "Не удалось найти подходящие проекты. Попробуйте обновить профиль через /start."
        )
        return ConversationHandler.END

    context.user_data["recommendations"] = data
    context.user_data.pop("pending_task_id", None)
    return await _show_program_from_message(update, context)


async def _show_program(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Format and send recommendation messages (from callback)."""
    data = context.user_data.get("recommendations")
    if not data:
        return ConversationHandler.END

    messages = _format_recommendations(data)
    must_recs = data.get("must_visit", [])
    has_if_time = bool(data.get("if_time"))
    keyboard = program_recommendation_keyboard(must_recs, has_if_time=has_if_time)

    chat_id = update.effective_chat.id

    # Send message parts
    for i, msg in enumerate(messages):
        if i == len(messages) - 1:
            await context.bot.send_message(
                chat_id=chat_id, text=msg, parse_mode="Markdown",
                reply_markup=keyboard,
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id, text=msg, parse_mode="Markdown",
            )

    # Send hint about features
    hint = (
        "Кликните на проект для подробностей. "
        "Я также могу помочь подготовить вопросы для докладчика — просто спросите в чате."
    )
    await context.bot.send_message(chat_id=chat_id, text=hint)

    return VIEW_PROGRAM


async def _show_program_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Format and send recommendation messages (from message)."""
    data = context.user_data.get("recommendations")
    if not data:
        return ConversationHandler.END

    messages = _format_recommendations(data)
    must_recs = data.get("must_visit", [])
    has_if_time = bool(data.get("if_time"))
    keyboard = program_recommendation_keyboard(must_recs, has_if_time=has_if_time)

    # Send message parts
    for i, msg in enumerate(messages):
        if i == len(messages) - 1:
            await update.message.reply_text(
                msg, parse_mode="Markdown", reply_markup=keyboard,
            )
        else:
            await update.message.reply_text(msg, parse_mode="Markdown")

    # Send hint about features
    hint = (
        "Кликните на проект для подробностей, или напишите в чат:\n"
        "- \"сравни проекты 1 и 3\" — матрица сравнения\n"
        "- \"подготовь вопросы к проекту 2\" — вопросы для Q&A\n"
        "- \"покажи follow-up\" — итоги и контакты"
    )
    await update.message.reply_text(hint)

    return VIEW_PROGRAM


AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "rebuild_profile",
            "description": (
                "Перезапустить профилирование — пользователь хочет изменить интересы, "
                "пересобрать профиль, начать заново или получить другие рекомендации"
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_project",
            "description": "Показать детали конкретного проекта по его номеру в рекомендациях",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_rank": {
                        "type": "integer",
                        "description": "Номер проекта в списке рекомендаций (1, 2, 3...)",
                    },
                },
                "required": ["project_rank"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_profile",
            "description": "Показать текущий профиль пользователя (теги, интересы, цели)",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_projects",
            "description": (
                "Сравнить несколько проектов — генерирует детальную матрицу сравнения. "
                "Используй когда пользователь просит сравнить, выбрать лучший из нескольких, "
                "или понять разницу между проектами."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project_ranks": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Номера проектов для сравнения (от 2 до 5)",
                    },
                    "criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Критерии сравнения (необязательно, будут подобраны автоматически)",
                    },
                },
                "required": ["project_ranks"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_questions",
            "description": (
                "Подготовить вопросы для Q&A к конкретному проекту. "
                "Используй когда пользователь хочет подготовиться к общению "
                "с автором проекта или задать вопросы на презентации."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project_rank": {
                        "type": "integer",
                        "description": "Номер проекта в списке рекомендаций",
                    },
                },
                "required": ["project_rank"],
            },
        },
    },
    # NOTE: follow-up tools temporarily disabled (not ready for production)
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_followup",
    #         "description": (
    #             "Получить follow-up пакет — итоги после Demo Day: "
    #             "список посещённых проектов, контакты авторов, шаблон письма. "
    #             "Только для гостей."
    #         ),
    #         "parameters": {"type": "object", "properties": {}, "required": []},
    #     },
    # },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_pipeline",
    #         "description": (
    #             "Показать бизнес-пайплайн — список проектов со статусами "
    #             "(заинтересован, на связи, переговоры, сделка). "
    #             "Только для бизнес-партнёров."
    #         ),
    #         "parameters": {"type": "object", "properties": {}, "required": []},
    #     },
    # },
]


async def view_program_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle callbacks in VIEW_PROGRAM: detail, pagination, update, check readiness."""
    query = update.callback_query
    await query.answer()

    data = query.data

    # Check readiness of pending generation task
    if data == "prof:check_ready":
        from app.worker.utils import get_task_status
        pending_task_id = context.user_data.get("pending_task_id")
        if not pending_task_id:
            await query.edit_message_text("Нет ожидающих задач. Используйте /start.")
            return VIEW_PROGRAM
        status = get_task_status(pending_task_id)
        if status["ready"]:
            if status.get("successful") and status.get("result"):
                context.user_data["recommendations"] = status["result"]
                context.user_data.pop("pending_task_id", None)
                await query.edit_message_text("Программа готова!")
                return await _show_program(update, context)
            else:
                context.user_data.pop("pending_task_id", None)
                await query.edit_message_text(
                    "К сожалению, генерация не удалась. "
                    "Попробуйте заново или измените профиль.",
                    reply_markup=retry_generation_keyboard(),
                )
                return VIEW_PROGRAM
        else:
            await query.edit_message_text(
                "Программа всё ещё генерируется. Подождите немного.",
                reply_markup=check_readiness_keyboard(),
            )
            return VIEW_PROGRAM

    # Retry failed generation
    if data == "prof:retry_gen":
        await query.edit_message_text("Перезапускаю генерацию программы... ⏳")
        return await _do_generate(update, context)

    # Show "if time" recommendations
    if data == "prof:show_if_time":
        recs_data = context.user_data.get("recommendations", {})
        if_time_msgs = _format_if_time(recs_data)
        if_time_recs = recs_data.get("if_time", [])
        keyboard = program_recommendation_keyboard(if_time_recs, has_if_time=False)
        chat_id = update.effective_chat.id
        for i, msg in enumerate(if_time_msgs):
            if i == len(if_time_msgs) - 1:
                await context.bot.send_message(
                    chat_id=chat_id, text=msg, parse_mode="Markdown",
                    reply_markup=keyboard,
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id, text=msg, parse_mode="Markdown",
                )
        return VIEW_PROGRAM

    # Pagination
    if data.startswith("recpage:"):
        page = int(data.split(":")[1])
        recs_data = context.user_data.get("recommendations", {})
        all_recs = recs_data.get("must_visit", []) + recs_data.get("if_time", [])
        await query.edit_message_reply_markup(
            reply_markup=program_recommendation_keyboard(all_recs, page=page)
        )
        return VIEW_PROGRAM

    # Project detail
    if data.startswith("pdetail:"):
        pid_short = data.split(":")[1]
        return await _show_project_detail(update, context, pid_short)

    # Update profile → restart NL profiling
    if data == "profile:update":
        return await _restart_nl_profiling_from_callback(update, context)

    return VIEW_PROGRAM


# ---------------------------------------------------------------------------
# Agent tool handlers
# ---------------------------------------------------------------------------


async def _handle_compare_projects(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tool_args: dict,
    all_recs: list[dict],
    is_business: bool,
) -> str:
    """Handle compare_projects tool call — generate comparison matrix."""
    from app.worker.tasks import generate_comparison_matrix_task
    from app.worker.utils import wait_for_task

    ranks = tool_args.get("project_ranks", [])
    if len(ranks) < 2:
        return "Для сравнения нужно минимум 2 проекта."
    if len(ranks) > 5:
        ranks = ranks[:5]

    # Map ranks to project IDs
    project_ids = []
    titles = []
    for rank in ranks:
        for rec in all_recs:
            if rec["rank"] == rank:
                project_ids.append(rec["project_id"])
                titles.append(rec["title"])
                break

    if len(project_ids) < 2:
        return "Не удалось найти указанные проекты в рекомендациях."

    # Get user for criteria
    tg_id = str(update.effective_user.id)
    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(session, tg_id)
        if not user:
            return "Пользователь не найден. Используйте /start."
        business_profile = None
        if is_business:
            business_profile = await business_followup_service.get_business_profile(
                session, user.id,
            )

    criteria = tool_args.get("criteria") or qa_service.get_default_criteria(
        user, business_profile
    )

    await update.message.reply_text("Генерирую матрицу сравнения...")

    task = generate_comparison_matrix_task.delay(
        str(user.id), project_ids, criteria,
    )
    completed, matrix = await wait_for_task(task.id, timeout=25, poll_interval=0.5)

    if not completed or matrix is None:
        return "Не удалось сгенерировать сравнение. Попробуйте позже."

    if isinstance(matrix, dict) and matrix.get("error"):
        return f"Ошибка сравнения: {matrix['error']}"

    text = qa_service.format_matrix_text(matrix, criteria)
    await safe_send_long_message(
        context.bot, update.effective_chat.id, text,
    )
    return ""  # already sent


async def _handle_generate_questions(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tool_args: dict,
    all_recs: list[dict],
) -> str:
    """Handle generate_questions tool call — Q&A for a project."""
    from app.worker.tasks import generate_qa_questions_task
    from app.worker.utils import wait_for_task

    rank = tool_args.get("project_rank", 1)
    project_id = None
    project_title = None
    for rec in all_recs:
        if rec["rank"] == rank:
            project_id = rec["project_id"]
            project_title = rec.get("title", "Проект")
            break

    if not project_id:
        return f"Проект #{rank} не найден в рекомендациях."

    tg_id = str(update.effective_user.id)
    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(session, tg_id)
        if not user:
            return "Пользователь не найден. Используйте /start."

    await update.message.reply_text(f"Генерирую вопросы для проекта #{rank}...")

    task = generate_qa_questions_task.delay(str(user.id), project_id)
    completed, questions = await wait_for_task(task.id, timeout=20, poll_interval=0.5)

    if not completed or not questions:
        return "Не удалось сгенерировать вопросы. Попробуйте позже."

    text = f"*Вопросы для проекта #{rank}:*\n_{_escape_markdown(project_title)}_\n\n"
    for i, q in enumerate(questions, 1):
        text += f"{i}. {q}\n\n"
    return text


async def _handle_get_followup(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> str:
    """Handle get_followup tool call — guest follow-up package."""
    role_code = context.user_data.get("pending_role_code", "")
    if role_code == RoleCode.BUSINESS.value:
        return "Follow-up пакет доступен только для гостей. Используйте get_pipeline."

    user_id = context.user_data.get("profile_user_id")
    event_id = context.user_data.get("profile_event_id")

    if not user_id or not event_id:
        return "Профиль не найден. Используйте /start."

    await update.message.reply_text("Формирую follow-up пакет...")

    async with async_session() as session:
        package = await followup_service.get_or_create_package(
            session, _uuid.UUID(user_id), _uuid.UUID(event_id),
        )
        await session.commit()

    if not package:
        return "Пока нет данных для follow-up. Сначала посетите проекты."

    text = followup_service.format_package_message(package)
    await safe_send_long_message(
        context.bot, update.effective_chat.id, text,
    )
    return ""  # already sent


async def _handle_get_pipeline(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> str:
    """Handle get_pipeline tool call — business partner pipeline."""
    role_code = context.user_data.get("pending_role_code", "")
    if role_code != RoleCode.BUSINESS.value:
        return "Пайплайн доступен только для бизнес-партнёров. Используйте get_followup."

    user_id = context.user_data.get("profile_user_id")
    event_id = context.user_data.get("profile_event_id")

    if not user_id or not event_id:
        return "Профиль не найден. Используйте /start."

    await update.message.reply_text("Загружаю бизнес-пайплайн...")

    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(
            session, str(update.effective_user.id),
        )
        if not user:
            return "Пользователь не найден. Используйте /start."

        followups = await business_followup_service.get_pipeline_projects(
            session, user.id, _uuid.UUID(event_id),
        )

        if not followups:
            added = await business_followup_service.init_pipeline_from_recommendations(
                session, user.id, _uuid.UUID(event_id),
            )
            if added:
                followups = await business_followup_service.get_pipeline_projects(
                    session, user.id, _uuid.UUID(event_id),
                )

        if not followups:
            return "Пайплайн пуст. Сначала получите рекомендации через /start."

        profile = await business_followup_service.get_business_profile(session, user.id)
        text = business_followup_service.format_pipeline_message(followups, profile)
        await session.commit()

    await safe_send_long_message(
        context.bot, update.effective_chat.id, text,
    )
    return ""  # already sent


async def view_program_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle text messages in VIEW_PROGRAM — LLM agent with tool calling."""
    from app.worker.tasks import agent_chat_task
    from app.worker.utils import get_task_status, wait_for_task

    # Check for pending recommendation generation task
    pending_task_id = context.user_data.get("pending_task_id")
    if pending_task_id:
        status = get_task_status(pending_task_id)
        if status["ready"]:
            if status.get("successful") and status.get("result"):
                context.user_data["recommendations"] = status["result"]
                context.user_data.pop("pending_task_id", None)
                await update.message.reply_text("Программа готова!")
                return await _show_program_from_message(update, context)
            else:
                context.user_data.pop("pending_task_id", None)
                await update.message.reply_text(
                    "К сожалению, генерация не удалась. "
                    "Попробуйте заново или измените профиль.",
                    reply_markup=retry_generation_keyboard(),
                )
                return VIEW_PROGRAM
        else:
            await update.message.reply_text(
                "Программа всё ещё генерируется. Подождите немного.",
                reply_markup=check_readiness_keyboard(),
            )
            return VIEW_PROGRAM

    user_message = update.message.text
    recs_data = context.user_data.get("recommendations", {})

    # Build context about profile and recommendations
    profile_info = ""
    nl_summary = ""
    user_id = context.user_data.get("profile_user_id")
    event_id = context.user_data.get("profile_event_id")
    if user_id and event_id:
        async with async_session() as session:
            profile = await profiling_service.get_or_create_profile(
                session, _uuid.UUID(user_id), _uuid.UUID(event_id)
            )
            profile_info = (
                f"Теги: {', '.join(profile.selected_tags) if profile.selected_tags else 'нет'}\n"
                f"Ключевые слова: {', '.join(profile.keywords) if profile.keywords else 'нет'}"
            )
            if profile.extra_data:
                ed = profile.extra_data
                nl_summary = ed.get("nl_summary", "")
                if ed.get("company"):
                    profile_info += f"\nКомпания: {ed['company']}"
                if ed.get("business_objectives"):
                    profile_info += f"\nБизнес-цели: {', '.join(ed['business_objectives'])}"
            if nl_summary:
                profile_info += f"\nО пользователе: {nl_summary}"

    # Build recommendations summary for LLM context
    recs_summary = ""
    all_recs = recs_data.get("must_visit", []) + recs_data.get("if_time", [])
    for rec in all_recs:
        recs_summary += (
            f"#{rec['rank']} {rec['title']} — {rec.get('relevance_score', 0)}% | "
            f"tags: {', '.join(rec.get('tags', [])[:3])} | "
            f"Зал {rec.get('room_number', '?')} | "
            f"{(rec.get('summary') or '')[:150]}\n"
        )

    role_code = context.user_data.get("pending_role_code", "")
    is_business = role_code == RoleCode.BUSINESS.value

    # NOTE: follow-up tools temporarily disabled (not ready for production)
    role_tools = ""

    system_prompt = (
        "Ты — AI-куратор Demo Day. Пользователь получил персональную программу проектов.\n"
        "Отвечай кратко, по делу, на русском. Без эмодзи.\n\n"
        f"РОЛЬ ПОЛЬЗОВАТЕЛЯ: {'бизнес-партнёр' if is_business else 'гость'}\n\n"
        "ИНСТРУМЕНТЫ (tools):\n"
        "- show_project — показать детали ОДНОГО проекта по номеру\n"
        "- show_profile — показать профиль пользователя\n"
        "- compare_projects — сравнить 2-5 проектов (генерирует матрицу сравнения)\n"
        "- generate_questions — подготовить вопросы для Q&A к проекту\n"
        f"{role_tools}"
        "- rebuild_profile — перезапустить профилирование\n\n"
        "ПРАВИЛА:\n"
        "- Для сравнения проектов ВСЕГДА вызывай compare_projects, НЕ пиши текстом\n"
        "- show_project — ТОЛЬКО для одного проекта, НЕ для сравнения\n"
        "- Если пользователь хочет изменить интересы — вызови rebuild_profile\n"
        "- Для простых вопросов о проектах отвечай текстом, используя данные из РЕКОМЕНДАЦИЙ\n"
        "- Помогай планировать маршрут по залам\n\n"
        f"ПРОФИЛЬ:\n{profile_info}\n\n"
        f"РЕКОМЕНДАЦИИ ({len(all_recs)} проектов):\n{recs_summary}"
    )

    # Maintain conversation history
    chat_history = context.user_data.get("program_chat", [])
    chat_history.append({"role": "user", "content": user_message})
    if len(chat_history) > 20:
        chat_history = chat_history[-20:]

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    # Submit agent chat to Celery
    task = agent_chat_task.delay(system_prompt, chat_history, AGENT_TOOLS)
    logger.info("Submitted agent_chat_task: task_id=%s", task.id)

    # Wait for result with shorter timeout (15s for chat responses)
    completed, response = await wait_for_task(task.id, timeout=15, poll_interval=0.5)

    if not completed or response is None:
        reply = "Обработка занимает больше времени. Попробуйте ещё раз через несколько секунд."
    else:
        try:
            if response["type"] == "tool_call":
                tool_name = response["tool_name"]
                tool_args = response.get("tool_args", {})

                if tool_name == "rebuild_profile":
                    # Reset chat and start NL profiling
                    context.user_data["program_chat"] = []
                    return await _restart_nl_profiling(update, context)

                elif tool_name == "show_project":
                    rank = tool_args.get("project_rank", 1)
                    # Find project by rank
                    for rec in all_recs:
                        if rec["rank"] == rank:
                            pid_short = rec["project_id"][:12]
                            # Send confirmation then show detail
                            await update.message.reply_text(f"Показываю проект #{rank}...")
                            return await _show_project_detail_from_text(update, context, pid_short)
                    reply = f"Проект #{rank} не найден в рекомендациях."

                elif tool_name == "show_profile":
                    reply = f"Ваш профиль:\n{profile_info}"

                elif tool_name == "compare_projects":
                    reply = await _handle_compare_projects(
                        update, context, tool_args, all_recs, is_business,
                    )

                elif tool_name == "generate_questions":
                    reply = await _handle_generate_questions(
                        update, context, tool_args, all_recs,
                    )

                # NOTE: follow-up tools temporarily disabled
                # elif tool_name == "get_followup":
                #     reply = await _handle_get_followup(update, context)
                #
                # elif tool_name == "get_pipeline":
                #     reply = await _handle_get_pipeline(update, context)

                else:
                    reply = "Неизвестное действие."

            else:
                reply = response.get("content", "")
                if not reply or not reply.strip():
                    reply = "Не удалось получить ответ. Попробуйте переформулировать вопрос."

        except Exception:
            logger.exception("Agent failed in VIEW_PROGRAM")
            reply = "Произошла ошибка. Попробуйте ещё раз или используйте кнопки."

    if reply:
        chat_history.append({"role": "assistant", "content": reply})
        context.user_data["program_chat"] = chat_history
        await update.message.reply_text(reply, parse_mode="Markdown")
    else:
        # Tool already sent the response (e.g. safe_send_long_message)
        chat_history.append({"role": "assistant", "content": "(результат отправлен)"})
        context.user_data["program_chat"] = chat_history

    return VIEW_PROGRAM


# =============================================================================
# VIEW_DETAIL state
# =============================================================================


async def _show_project_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, pid_short: str) -> int:
    """Show full project detail (from callback)."""
    query = update.callback_query
    profile_id = _uuid.UUID(context.user_data.get("profile_id", ""))

    # Find full project_id from recommendations
    recs_data = context.user_data.get("recommendations", {})
    all_recs = recs_data.get("must_visit", []) + recs_data.get("if_time", [])
    project_id = None
    project_rank = None
    for rec in all_recs:
        if rec["project_id"].startswith(pid_short):
            project_id = _uuid.UUID(rec["project_id"])
            project_rank = rec.get("rank")
            break

    if not project_id:
        await query.edit_message_text("Проект не найден.")
        return VIEW_PROGRAM

    async with async_session() as session:
        detail = await profiling_service.get_project_detail(session, profile_id, project_id)

    if not detail:
        await query.edit_message_text("Проект не найден в подборке.")
        return VIEW_PROGRAM

    if detail.get("room_number"):
        room_info = f"Зал {detail['room_number']}: {_escape_markdown(detail['room_name'])}"
    else:
        room_info = "Зал: н/д"
    tags_str = ", ".join(detail.get("tags", []))
    score_pct = min(int(detail["relevance_score"]), 100) if detail["relevance_score"] > 0 else 0

    title = _escape_markdown(detail['title'])

    # Use LLM summary as main description, fallback to truncated original
    if detail.get("llm_summary"):
        summary = _escape_markdown(detail['llm_summary'])
    else:
        summary = _escape_markdown(_truncate(detail['description'], 300))

    text = (
        f"*{title}*\n\n"
        f"{summary}\n\n"
        f"Теги: {tags_str}\n"
        f"{room_info}\n"
        f"Релевантность: {score_pct}%"
    )

    # Store project info for Q&A
    context.user_data["current_project_id"] = str(project_id)
    context.user_data["current_project_title"] = detail['title']
    context.user_data["current_project_rank"] = project_rank

    pid_short_btn = str(project_id)[:12]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Подготовить вопросы", callback_data=f"qa:prep:{pid_short_btn}")],
        # [contact_button(project_id)],  # temporarily disabled
        [InlineKeyboardButton("Назад к программе", callback_data="prof:back_program")],
    ])

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=keyboard,
    )
    return VIEW_DETAIL


async def _show_project_detail_from_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, pid_short: str
) -> int:
    """Show project detail triggered from text message (not callback)."""
    profile_id_str = context.user_data.get("profile_id", "")
    if not profile_id_str:
        await update.message.reply_text("Профиль не найден. Используйте /start.")
        return VIEW_PROGRAM

    profile_id = _uuid.UUID(profile_id_str)

    # Find full project_id from recommendations
    recs_data = context.user_data.get("recommendations", {})
    all_recs = recs_data.get("must_visit", []) + recs_data.get("if_time", [])
    project_id = None
    project_rank = None
    for rec in all_recs:
        if rec["project_id"].startswith(pid_short):
            project_id = _uuid.UUID(rec["project_id"])
            project_rank = rec.get("rank")
            break

    if not project_id:
        await update.message.reply_text("Проект не найден.")
        return VIEW_PROGRAM

    async with async_session() as session:
        detail = await profiling_service.get_project_detail(session, profile_id, project_id)

    if not detail:
        await update.message.reply_text("Проект не найден в подборке.")
        return VIEW_PROGRAM

    room_info = f"Зал {detail['room_number']}: {detail['room_name']}" if detail.get("room_number") else ""
    tags_str = ", ".join(detail.get("tags", []))
    score_pct = min(int(detail["relevance_score"]), 100) if detail["relevance_score"] > 0 else 0

    # Use LLM summary as main description, fallback to truncated original
    if detail.get("llm_summary"):
        summary = detail['llm_summary']
    else:
        summary = _truncate(detail['description'], 300)

    text = (
        f"*{_escape_markdown(detail['title'])}*\n\n"
        f"{_escape_markdown(summary)}\n\n"
        f"Теги: {tags_str}\n"
        f"{room_info}\n"
        f"Релевантность: {score_pct}%"
    )

    # Store project info for Q&A
    context.user_data["current_project_id"] = str(project_id)
    context.user_data["current_project_title"] = detail['title']
    context.user_data["current_project_rank"] = project_rank

    pid_short_btn = str(project_id)[:12]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Подготовить вопросы", callback_data=f"qa:prep:{pid_short_btn}")],
        # [contact_button(project_id)],  # temporarily disabled
        [InlineKeyboardButton("Назад к программе", callback_data="prof:back_program")],
    ])

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
    return VIEW_DETAIL


async def back_to_program_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to program view from detail."""
    query = update.callback_query
    await query.answer()
    return await _show_program(update, context)


async def qa_prep_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Prepare questions' button — generate Q&A suggestions for project."""
    from app.worker.tasks import generate_qa_questions_task
    from app.worker.utils import wait_for_task

    query = update.callback_query
    await query.answer()

    # Parse project_id from callback data (qa:prep:{pid_short})
    pid_short = query.data.split(":")[-1]

    # Find full project_id from recommendations
    recs_data = context.user_data.get("recommendations", {})
    all_recs = recs_data.get("must_visit", []) + recs_data.get("if_time", [])
    project_id = None
    project_title = None
    for rec in all_recs:
        if rec["project_id"].startswith(pid_short):
            project_id = rec["project_id"]
            project_title = rec.get("title", "Проект")
            break

    if not project_id:
        await query.edit_message_text("Проект не найден.")
        return VIEW_PROGRAM

    await query.edit_message_text("Генерирую вопросы...")

    # Get user_id from DB
    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(session, str(query.from_user.id))
        if not user:
            await query.edit_message_text("Пользователь не найден. Используйте /start.")
            return VIEW_PROGRAM
        user_id = str(user.id)

    # Submit Q&A generation to Celery
    task = generate_qa_questions_task.delay(user_id, project_id)
    logger.info("Submitted generate_qa_questions_task: task_id=%s", task.id)

    # Wait for result with timeout (20s for Q&A generation)
    completed, questions = await wait_for_task(task.id, timeout=20, poll_interval=0.5)

    if not completed or questions is None:
        questions = ["Не удалось сгенерировать вопросы. Попробуйте позже."]

    # Format response
    text = f"*Вопросы для проекта:*\n_{_escape_markdown(project_title)}_\n\n"
    for i, q in enumerate(questions, 1):
        text += f"{i}. {q}\n\n"

    pid_short_btn = str(project_id)[:12]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Ещё вопросы", callback_data=f"qa:more:{pid_short_btn}")],
        [InlineKeyboardButton("Назад к проекту", callback_data=f"pdetail:{pid_short_btn}")],
        [InlineKeyboardButton("Назад к программе", callback_data="prof:back_program")],
    ])

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    return VIEW_DETAIL


async def qa_more_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'More questions' button — regenerate questions."""
    # Reuse the same logic
    return await qa_prep_callback(update, context)


# =============================================================================
# NL_REBUILD state (profile rebuild from agent mode)
# =============================================================================


async def _restart_nl_profiling(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Restart NL profiling flow from agent mode without role change (from message)."""
    tg_user = update.effective_user
    telegram_user_id = str(tg_user.id)

    auth = await _check_guest_or_business(telegram_user_id)
    if not auth:
        await update.message.reply_text(
            "Сначала выберите роль через /start"
        )
        return VIEW_PROGRAM

    user, event, role_code = auth

    # Reset profiling state
    context.user_data["profile_user_id"] = str(user.id)
    context.user_data["profile_event_id"] = str(event.id)
    context.user_data["rebuild_topics"] = set()
    context.user_data["rebuild_conversation"] = []
    context.user_data["pending_role_code"] = role_code
    context.user_data.pop("recommendations", None)
    context.user_data.pop("program_chat", None)

    await update.message.reply_text(
        "Пересобираем профиль.\n\n"
        "Что вас интересует на Demo Day?\n"
        "Напишите текстом или выберите темы:",
        reply_markup=nl_topic_buttons(prefix="reb_nl", topics=await _get_topics()),
    )

    return NL_REBUILD


async def _restart_nl_profiling_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Restart NL profiling flow from agent mode without role change (from callback)."""
    query = update.callback_query
    tg_user = query.from_user
    telegram_user_id = str(tg_user.id)

    auth = await _check_guest_or_business(telegram_user_id)
    if not auth:
        await query.edit_message_text(
            "Сначала выберите роль через /start"
        )
        return VIEW_PROGRAM

    user, event, role_code = auth

    # Reset profiling state
    context.user_data["profile_user_id"] = str(user.id)
    context.user_data["profile_event_id"] = str(event.id)
    context.user_data["rebuild_topics"] = set()
    context.user_data["rebuild_conversation"] = []
    context.user_data["pending_role_code"] = role_code
    context.user_data.pop("recommendations", None)
    context.user_data.pop("program_chat", None)

    await query.edit_message_text(
        "Пересобираем профиль.\n\n"
        "Что вас интересует на Demo Day?\n"
        "Напишите текстом или выберите темы:",
        reply_markup=nl_topic_buttons(prefix="reb_nl", topics=await _get_topics()),
    )

    return NL_REBUILD


async def _reb_nl_topic_buttons_with_selection(selected: set[str]):
    """Rebuild NL topic buttons with checkmarks (rebuild mode)."""
    topics = await _get_topics()
    buttons = []
    row = []
    for tag_key, display in topics:
        prefix = "✓ " if tag_key in selected else ""
        row.append(InlineKeyboardButton(
            f"{prefix}{display}", callback_data=f"reb_nl:topic:{tag_key}",
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Готово →", callback_data="reb_nl:done")])
    return InlineKeyboardMarkup(buttons)


async def nl_rebuild_topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle topic toggles in NL_REBUILD state."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "reb_nl:done":
        topics = context.user_data.get("rebuild_topics", set())
        conv = context.user_data.get("rebuild_conversation", [])

        if not topics and not conv:
            await query.edit_message_text(
                "Укажите хотя бы одну тему или напишите, что вас интересует.",
                reply_markup=nl_topic_buttons(prefix="reb_nl", topics=await _get_topics()),
            )
            return NL_REBUILD

        if topics:
            display_labels = [_FALLBACK_TOPIC_LABELS.get(t, t) for t in topics]
            topic_msg = f"Меня интересуют: {', '.join(display_labels)}"
            conv.append({"role": "user", "content": topic_msg})
            context.user_data["rebuild_conversation"] = conv

        return await _rebuild_agent_turn(update, context, conv)

    # Toggle topic
    _, _, topic_key = data.split(":", 2)
    topics = context.user_data.get("rebuild_topics", set())
    if topic_key in topics:
        topics.discard(topic_key)
    else:
        topics.add(topic_key)
    context.user_data["rebuild_topics"] = topics

    await query.edit_message_reply_markup(
        reply_markup=await _reb_nl_topic_buttons_with_selection(topics)
    )
    return NL_REBUILD


async def nl_rebuild_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle free text in NL_REBUILD state."""
    user_text = update.message.text
    conv = context.user_data.get("rebuild_conversation", [])
    conv.append({"role": "user", "content": user_text})
    context.user_data["rebuild_conversation"] = conv
    return await _rebuild_agent_turn(update, context, conv, is_message=True)


async def _rebuild_agent_turn(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    conversation: list[dict],
    is_message: bool = False,
) -> int:
    """Process NL rebuild conversation with LLM."""
    from app.worker.tasks import chat_for_profile_task
    from app.worker.utils import wait_for_task

    selected_tags = list(context.user_data.get("rebuild_topics", set()))
    role_code = context.user_data.get("pending_role_code")

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    # Submit to Celery
    task = chat_for_profile_task.delay(
        conversation, selected_tags, role_code=role_code,
    )

    # Wait for result
    completed, result = await wait_for_task(task.id, timeout=15, poll_interval=0.5)

    if not completed or result is None:
        result = {"action": "reply", "message": "Расскажите подробнее о ваших интересах."}

    if result["action"] == "profile":
        context.user_data["rebuild_profile"] = result
        return await _show_rebuild_confirmation(update, context, result, is_message)

    # Continue conversation
    reply_text = result["message"]
    conversation.append({"role": "assistant", "content": reply_text})
    context.user_data["rebuild_conversation"] = conversation

    if not is_message:
        await update.callback_query.edit_message_reply_markup(reply_markup=None)
    reb_kb = nl_topic_buttons(prefix="reb_nl", topics=await _get_topics())
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=reply_text,
        reply_markup=reb_kb,
    )

    return NL_REBUILD


async def _show_rebuild_confirmation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    profile_data: dict,
    is_message: bool = False,
) -> int:
    """Show rebuilt profile for confirmation."""
    summary = profile_data.get("summary", "")
    interests = profile_data.get("interests", [])
    goals = profile_data.get("goals", [])

    button_tags = list(context.user_data.get("rebuild_topics", set()))
    all_tags = list(dict.fromkeys(button_tags + interests))

    parts = []
    if summary:
        parts.append(summary)
    if all_tags:
        parts.append(f"Теги: {', '.join(all_tags)}")
    if goals:
        parts.append(f"Цели: {', '.join(goals)}")
    if not parts:
        parts.append("Общий интерес к Demo Day")

    text = "Новый профиль:\n\n" + "\n".join(parts) + "\n\nВсё верно?"

    if not is_message:
        await update.callback_query.edit_message_reply_markup(reply_markup=None)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=confirm_nl_profile_keyboard(prefix="reb_nlconf"),
    )

    return NL_REBUILD_CONFIRM


# =============================================================================
# NL_REBUILD_CONFIRM state
# =============================================================================


async def nl_rebuild_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle rebuild profile confirmation."""
    query = update.callback_query
    await query.answer()

    _, choice = query.data.split(":", 1)

    if choice == "retry":
        context.user_data["rebuild_topics"] = set()
        context.user_data["rebuild_conversation"] = []
        await query.edit_message_text(
            "Давайте заново.\n\nЧто вас интересует на Demo Day?",
            reply_markup=nl_topic_buttons(prefix="reb_nl", topics=await _get_topics()),
        )
        return NL_REBUILD

    # Save profile and regenerate recommendations
    tg_user = query.from_user
    telegram_user_id = str(tg_user.id)
    profile_data = context.user_data.get("rebuild_profile", {})
    interests = profile_data.get("interests", [])
    button_tags = list(context.user_data.get("rebuild_topics", set()))

    conversation = context.user_data.get("rebuild_conversation", [])
    raw_text = "\n".join(
        f"{'Гость' if m['role'] == 'user' else 'Куратор'}: {m['content']}"
        for m in conversation
    )

    all_tags = list(dict.fromkeys(button_tags + interests))

    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(session, telegram_user_id)
        event = await user_service.get_current_event(session)

        if not user or not event:
            await query.edit_message_text("Ошибка. Попробуйте /start заново.")
            return ConversationHandler.END

        extra_data = {}
        summary = profile_data.get("summary")
        if summary:
            extra_data["nl_summary"] = summary
        if not extra_data:
            extra_data = None

        profile = await profiling_service.get_or_create_profile(session, user.id, event.id)
        await profiling_service.save_profile(
            session, profile,
            selected_tags=all_tags,
            keywords=profile_data.get("goals", []),
            raw_text=raw_text or None,
            extra_data=extra_data,
        )
        context.user_data["profile_id"] = str(profile.id)
        context.user_data["profile_user_id"] = str(user.id)
        context.user_data["profile_event_id"] = str(event.id)

    logger.info("Profile rebuilt: tg_id=%s tags=%s", telegram_user_id, all_tags)

    await query.edit_message_text("Профиль обновлён. Генерирую новые рекомендации...")

    # Generate new recommendations
    return await _do_generate(update, context)


# =============================================================================
# Cancel
# =============================================================================


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END


# =============================================================================
# Orphan message handler (after container restart, conversation state is lost)
# =============================================================================


async def orphan_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch text messages from users not in any ConversationHandler.

    After a container restart the in-memory conversation state is wiped.
    If the user has a profile we silently re-enter them into the agent;
    otherwise we ask them to /start.
    """
    tg_user = update.effective_user
    if not tg_user:
        return

    telegram_user_id = str(tg_user.id)

    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(session, telegram_user_id)
        event = await user_service.get_current_event(session)

        if not user or not event:
            await update.message.reply_text(
                "Отправьте /start для начала работы с ботом."
            )
            return

        role = await user_service.get_user_role_with_info(session, user.id, event.id)
        if not role:
            await update.message.reply_text(
                "Отправьте /start для начала работы с ботом."
            )
            return

        profile = await profiling_service.get_or_create_profile(session, user.id, event.id)
        has_profile = bool(profile.selected_tags)

    if not has_profile:
        await update.message.reply_text(
            "Отправьте /start для продолжения."
        )
        return

    # User has a profile — tell them to /start to restore session
    await update.message.reply_text(
        "Сессия была перезапущена. Отправьте /start — я восстановлю вашу программу."
    )


# =============================================================================
# Handler factory
# =============================================================================


def get_onboarding_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            CommandHandler("role", start_command),
        ],
        states={
            CHOOSE_ROLE: [
                CallbackQueryHandler(role_chosen, pattern=r"^role:"),
            ],
            CHOOSE_SUBTYPE: [
                CallbackQueryHandler(subtype_chosen, pattern=r"^subtype:"),
            ],
            ENTER_SUBTYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_subtype_handler),
            ],
            ONBOARD_NL_PROFILE: [
                CallbackQueryHandler(onb_nl_topic_callback, pattern=r"^onb_nl:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, onb_nl_free_text),
            ],
            ONBOARD_CONFIRM: [
                CallbackQueryHandler(onb_confirm_profile_callback, pattern=r"^onb_nlconf:"),
            ],
            CONFIRM_CHANGE: [
                CallbackQueryHandler(confirm_change, pattern=r"^(change:|prof:resume|prof:restart)"),
            ],
            VIEW_PROGRAM: [
                CallbackQueryHandler(
                    view_program_callback,
                    pattern=r"^(pdetail:|recpage:|profile:update|prof:show_if_time|prof:check_ready|prof:retry_gen|noop)",
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, view_program_text),
            ],
            VIEW_DETAIL: [
                CallbackQueryHandler(qa_prep_callback, pattern=r"^qa:prep:"),
                CallbackQueryHandler(qa_more_callback, pattern=r"^qa:more:"),
                CallbackQueryHandler(view_program_callback, pattern=r"^pdetail:"),
                CallbackQueryHandler(back_to_program_callback, pattern=r"^prof:back_program$"),
                # CallbackQueryHandler(contact_request_callback, pattern=r"^contact:req:"),  # temporarily disabled
            ],
            NL_REBUILD: [
                CallbackQueryHandler(nl_rebuild_topic_callback, pattern=r"^reb_nl:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, nl_rebuild_text),
            ],
            NL_REBUILD_CONFIRM: [
                CallbackQueryHandler(nl_rebuild_confirm_callback, pattern=r"^reb_nlconf:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
        allow_reentry=True,
    )
