"""Onboarding ConversationHandler — NL-first with guest subtypes.

Flow:
  /start → [🎓 Гость] [💼 Партнёр]

  If Guest:
    → [🎓 Студент] [📚 Абитуриент] [Другое — ввести текстом]
    → (if "Другое" — free text entry for custom subtype)

  Then for both Guest and Partner:
    → Free text + topic quick-pick buttons
    → LLM extracts profile
    → Confirmation → trigger profiling / recommendations

States:
  CHOOSE_ROLE → CHOOSE_SUBTYPE → ENTER_SUBTYPE → NL_PROFILE → CONFIRM_PROFILE
"""

import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.bot.keyboards import (
    confirm_change_keyboard,
    confirm_nl_profile_keyboard,
    guest_subtype_keyboard,
    nl_topic_buttons,
    role_keyboard,
    start_profiling_keyboard,
)
from app.database import async_session
from app.models.role import ROLE_DISPLAY_NAMES, RoleCode
from app.models.user import GUEST_SUBTYPE_DISPLAY, GuestSubtype
from app.services import profiling_service, user_service

logger = logging.getLogger(__name__)

# Conversation states
CHOOSE_ROLE, CHOOSE_SUBTYPE, ENTER_SUBTYPE, NL_PROFILE, CONFIRM_PROFILE, CONFIRM_CHANGE = range(6)

# Mapping of quick-pick topic callback data to display labels
TOPIC_LABELS = {
    "ai_ml": "AI / ML",
    "nlp": "NLP",
    "cv": "Computer Vision",
    "edtech": "EdTech",
    "fintech": "FinTech",
    "agents": "Агенты",
    "medtech": "MedTech",
    "security": "Security",
}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command — entry point for onboarding."""
    # Check if this is an expert deep link: /start expert
    if context.args and context.args[0] == "expert":
        from app.bot.handlers.expert_assignment import handle_expert_start
        return await handle_expert_start(update, context)

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
            await update.message.reply_text("Нет активного события. Попробуйте позже.")
            return ConversationHandler.END

        role = await user_service.get_user_role_with_info(session, user.id, event.id)

    logger.info("start: user=%s tg_id=%s has_role=%s", full_name, telegram_user_id, role is not None)

    if role:
        role_name = ROLE_DISPLAY_NAMES.get(RoleCode(role.code), role.code)
        context.user_data["current_role"] = role.code
        context.user_data["event_id"] = str(event.id)
        await update.message.reply_text(
            f"С возвращением, {full_name}!\n"
            f"Ваша роль: {role_name}\n\n"
            f"Хотите сменить роль?",
            reply_markup=confirm_change_keyboard(),
        )
        return CONFIRM_CHANGE

    # Reset onboarding state
    context.user_data["event_id"] = str(event.id)
    context.user_data["nl_topics"] = set()
    context.user_data["nl_conversation"] = []

    await update.message.reply_text(
        f"Добро пожаловать на Demo Day, {full_name}!\n\n"
        f"Кто вы?",
        reply_markup=role_keyboard(),
    )
    return CHOOSE_ROLE


# --- CHOOSE_ROLE state ---


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
        "Расскажите, что вас интересует на Demo Day?\n\n"
        "Напишите свободным текстом или выберите темы кнопками:",
        reply_markup=nl_topic_buttons(),
    )
    return NL_PROFILE


# --- CHOOSE_SUBTYPE state ---


async def subtype_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle guest subtype selection."""
    query = update.callback_query
    await query.answer()

    _, subtype_str = query.data.split(":", 1)
    guest_subtype = GuestSubtype(subtype_str)

    tg_user = query.from_user
    telegram_user_id = str(tg_user.id)

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
        f"Отлично, {subtype_name}!\n\n"
        f"Расскажите, что вас интересует на Demo Day?\n"
        f"Напишите свободным текстом или выберите темы кнопками:",
        reply_markup=nl_topic_buttons(),
    )
    return NL_PROFILE


# --- ENTER_SUBTYPE state (free text for "Другое") ---


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
        f"Понятно, {custom_subtype}!\n\n"
        f"Расскажите, что вас интересует на Demo Day?\n"
        f"Напишите свободным текстом или выберите темы кнопками:",
        reply_markup=nl_topic_buttons(),
    )
    return NL_PROFILE


# --- NL_PROFILE state ---


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


async def nl_topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle topic button toggles and 'done' in NL profiling."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "nl:done":
        # User pressed "Готово" with selected topics — inject as user message
        topics = context.user_data.get("nl_topics", set())
        if not topics and not _get_conversation(context):
            await query.edit_message_text(
                "Укажите хотя бы одну тему или напишите текстом, что вас интересует.",
                reply_markup=nl_topic_buttons(),
            )
            return NL_PROFILE

        if topics:
            topic_labels = [TOPIC_LABELS.get(t, t) for t in topics]
            topic_msg = f"Меня интересуют темы: {', '.join(topic_labels)}"
            conv = _add_to_conversation(context, "user", topic_msg)
        else:
            conv = _get_conversation(context)

        return await _agent_turn(update, context, conv)

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
        reply_markup=_nl_topic_buttons_with_selection(topics)
    )
    return NL_PROFILE


async def nl_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle free text input in NL profiling — conversational agent."""
    user_text = update.message.text
    conv = _add_to_conversation(context, "user", user_text)
    return await _agent_turn(update, context, conv, is_message=True)


def _nl_topic_buttons_with_selection(selected: set[str]):
    """Rebuild NL topic buttons with checkmarks for selected topics."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    topics = [
        ("AI / ML", "nl:topic:ai_ml"),
        ("NLP", "nl:topic:nlp"),
        ("Computer Vision", "nl:topic:cv"),
        ("EdTech", "nl:topic:edtech"),
        ("FinTech", "nl:topic:fintech"),
        ("Агенты", "nl:topic:agents"),
        ("MedTech", "nl:topic:medtech"),
        ("Security", "nl:topic:security"),
    ]
    buttons = []
    row = []
    for label, cb in topics:
        key = cb.split(":")[-1]
        prefix = "✓ " if key in selected else ""
        row.append(InlineKeyboardButton(f"{prefix}{label}", callback_data=cb))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Готово →", callback_data="nl:done")])
    return InlineKeyboardMarkup(buttons)


async def _agent_turn(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    conversation: list[dict],
    is_message: bool = False,
) -> int:
    """Send conversation to LLM agent, handle reply or profile extraction."""
    result = await profiling_service.chat_for_profile(conversation)

    if result["action"] == "profile":
        # Agent decided we have enough info — show confirmation
        context.user_data["extracted_profile"] = result
        return await _show_profile_confirmation(update, context, result, is_message)

    # Agent wants to continue the conversation
    reply_text = result["message"]
    _add_to_conversation(context, "assistant", reply_text)

    if is_message:
        await update.message.reply_text(reply_text)
    else:
        await update.callback_query.edit_message_text(reply_text)

    return NL_PROFILE


async def _show_profile_confirmation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    profile_data: dict,
    is_message: bool = False,
) -> int:
    """Show extracted profile for user confirmation."""
    summary = profile_data.get("summary", "")
    interests = profile_data.get("interests", [])
    goals = profile_data.get("goals", [])

    confirm_parts = []
    if summary:
        confirm_parts.append(summary)
    if interests:
        confirm_parts.append(f"Интересы: {', '.join(interests)}")
    if goals:
        confirm_parts.append(f"Цели: {', '.join(goals)}")

    if not confirm_parts:
        confirm_parts.append("Общий интерес к Demo Day")

    confirm_text = "Ваш профиль:\n\n" + "\n".join(confirm_parts) + "\n\nВсё верно?"

    if is_message:
        await update.message.reply_text(
            confirm_text,
            reply_markup=confirm_nl_profile_keyboard(),
        )
    else:
        await update.callback_query.edit_message_text(
            confirm_text,
            reply_markup=confirm_nl_profile_keyboard(),
        )

    return CONFIRM_PROFILE


# --- CONFIRM_PROFILE state ---


async def confirm_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle profile confirmation: yes → save & trigger profiling, retry → back to NL."""
    query = update.callback_query
    await query.answer()

    _, choice = query.data.split(":", 1)

    if choice == "retry":
        context.user_data["nl_topics"] = set()
        context.user_data["nl_conversation"] = []
        await query.edit_message_text(
            "Расскажите, что вас интересует на Demo Day?\n"
            "Напишите свободным текстом или выберите темы кнопками:",
            reply_markup=nl_topic_buttons(),
        )
        return NL_PROFILE

    # choice == "yes" — save profile and trigger profiling
    tg_user = query.from_user
    telegram_user_id = str(tg_user.id)
    profile_data = context.user_data.get("extracted_profile", {})
    interests = profile_data.get("interests", [])
    topics = context.user_data.get("nl_topics", set())
    topic_labels = [TOPIC_LABELS.get(t, t) for t in topics]

    # Build raw_text from full conversation history
    conversation = context.user_data.get("nl_conversation", [])
    raw_text = "\n".join(
        f"{'Гость' if m['role'] == 'user' else 'Куратор'}: {m['content']}"
        for m in conversation
    )

    # selected_tags = what user clicked (buttons)
    # extracted_tags = what LLM extracted from the interview
    selected_tags = list(dict.fromkeys(topic_labels))
    extracted_tags = list(dict.fromkeys(interests))

    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(session, telegram_user_id)
        event = await user_service.get_current_event(session)

        if not user or not event:
            await query.edit_message_text("Ошибка. Попробуйте /start заново.")
            return ConversationHandler.END

        # Save guest profile with extracted data
        profile = await profiling_service.get_or_create_profile(
            session, user.id, event.id
        )
        await profiling_service.save_profile(
            session,
            profile,
            selected_tags=selected_tags,
            extracted_tags=extracted_tags,
            keywords=profile_data.get("goals", []),
            raw_text=raw_text or None,
        )

    logger.info(
        "Profile confirmed via NL: tg_id=%s selected=%s extracted=%s",
        telegram_user_id, selected_tags, extracted_tags,
    )

    await query.edit_message_text(
        "Профиль сохранён! Хотите получить персональную программу?",
        reply_markup=start_profiling_keyboard(),
    )
    return ConversationHandler.END


# --- CONFIRM_CHANGE state (returning user) ---


async def confirm_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    _, choice = query.data.split(":", 1)

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


# --- Cancel ---


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END


# --- Handler factory ---


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
            NL_PROFILE: [
                CallbackQueryHandler(nl_topic_callback, pattern=r"^nl:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, nl_free_text),
            ],
            CONFIRM_PROFILE: [
                CallbackQueryHandler(confirm_profile_callback, pattern=r"^nlconf:"),
            ],
            CONFIRM_CHANGE: [
                CallbackQueryHandler(confirm_change, pattern=r"^change:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
