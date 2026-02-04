"""Guest profiling ConversationHandler (EPIC-005).

States: CHOOSE_TAGS → ENTER_TEXT → CONFIRM_PROFILE → GENERATE_PROGRAM → VIEW_PROGRAM → VIEW_DETAIL
"""

import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.bot.handlers.contact import contact_button, contact_request_callback
from app.bot.keyboards import (
    back_to_program_keyboard,
    confirm_interests_keyboard,
    generate_program_keyboard,
    program_recommendation_keyboard,
    start_profiling_keyboard,
    tag_selection_keyboard,
    update_profile_keyboard,
)
from app.database import async_session
from app.models.role import RoleCode
from app.services import profiling_service, user_service

logger = logging.getLogger(__name__)

# Conversation states
(
    CHOOSE_TAGS,
    ENTER_TEXT,
    CONFIRM_PROFILE,
    GENERATE_PROGRAM,
    VIEW_PROGRAM,
    VIEW_DETAIL,
) = range(6)

MAX_MESSAGE_LEN = 4096


# --- Helpers ---


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


async def _load_tags(event_id) -> list[tuple[str, int]]:
    """Load available tags for the event."""
    async with async_session() as session:
        return await profiling_service.get_available_tags(session, event_id)


def _truncate(text: str, limit: int) -> str:
    """Truncate text at sentence boundary, fallback to word boundary."""
    if not text or len(text) <= limit:
        return text
    # Try to cut at last sentence end within limit
    chunk = text[:limit]
    for sep in (". ", "! ", "? ", ".\n"):
        pos = chunk.rfind(sep)
        if pos > limit // 3:
            return chunk[: pos + 1]
    # Fallback: cut at last space
    pos = chunk.rfind(" ")
    if pos > limit // 3:
        return chunk[:pos] + "..."
    return chunk + "..."


def _escape_markdown(text: str) -> str:
    """Escape Markdown special characters."""
    if not text:
        return ""
    for char in ['*', '_', '`', '[', ']', '(', ')']:
        text = text.replace(char, '\\' + char)
    return text


def _format_interests(selected: list[str], extracted: list[str], keywords: list[str]) -> str:
    """Format interests for confirmation message."""
    all_tags = list(dict.fromkeys(selected + extracted))  # deduplicate, preserve order
    parts = []
    if all_tags:
        parts.append(", ".join(all_tags))
    if keywords:
        parts.append(", ".join(keywords))
    return ", ".join(parts) if parts else "(пусто)"


def _format_recommendations(data: dict) -> list[str]:
    """Format must-visit recommendations into message parts (respecting 4096 char limit)."""
    messages = []

    must_text = "🎯 *Обязательно посетить:*\n\n"
    for rec in data.get("must_visit", []):
        title = _escape_markdown(rec["title"])
        summary = _escape_markdown(_truncate(rec["summary"], 200) if rec["summary"] else "")
        author = _escape_markdown(rec.get("author", ""))
        room_info = f"Зал {rec['room_number']}" if rec.get("room_number") else "Зал: н/д"
        tags_str = ", ".join(rec.get("tags", [])[:4])
        conflict = ""
        if rec.get("conflict_rooms"):
            conflict = f" ⚠️ Параллельно с Зал {', '.join(str(r) for r in rec['conflict_rooms'][:3])}"

        score = int(rec.get("relevance_score", 0))
        entry = (
            f"*{rec['rank']}. {title}* ({score}%)\n"
            f"{summary}\n"
            f"📍 {room_info} · {tags_str} · {author}{conflict}\n\n"
        )
        must_text += entry

    # Split long must-visit into multiple messages
    if len(must_text) > MAX_MESSAGE_LEN:
        # Rough split by half of entries
        must_recs = data.get("must_visit", [])
        mid = len(must_recs) // 2
        part1 = "🎯 *Обязательно посетить:*\n\n"
        part2 = ""
        for i, rec in enumerate(must_recs):
            title = _escape_markdown(rec["title"])
            summary = _escape_markdown(_truncate(rec["summary"], 200) if rec["summary"] else "")
            author = _escape_markdown(rec.get("author", ""))
            room_info = f"Зал {rec['room_number']}" if rec.get("room_number") else "Зал: н/д"
            tags_str = ", ".join(rec.get("tags", [])[:4])
            conflict = ""
            if rec.get("conflict_rooms"):
                conflict = f" ⚠️ Параллельно с Зал {', '.join(str(r) for r in rec['conflict_rooms'][:3])}"
            entry = (
                f"*{rec['rank']}. {title}*\n"
                f"{summary}\n"
                f"📍 {room_info} · {tags_str} · {author}{conflict}\n\n"
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
    if_time_text = "⏰ *Если останется время:*\n\n"
    for rec in data.get("if_time", []):
        title = _escape_markdown(rec["title"])
        summary = _escape_markdown(_truncate(rec["summary"], 180) if rec["summary"] else "")
        room_info = f"Зал {rec['room_number']}" if rec.get("room_number") else "Зал: н/д"
        tags_str = ", ".join(rec.get("tags", [])[:3])

        score = int(rec.get("relevance_score", 0))
        entry = (
            f"*{rec['rank']}. {title}* ({score}%)\n"
            f"{summary}\n"
            f"📍 {room_info} · {tags_str}\n\n"
        )
        if_time_text += entry

    if len(if_time_text) > MAX_MESSAGE_LEN:
        if_recs = data.get("if_time", [])
        mid = len(if_recs) // 2
        part1 = "⏰ *Если останется время:*\n\n"
        part2 = ""
        for i, rec in enumerate(if_recs):
            title = _escape_markdown(rec["title"])
            summary = _escape_markdown(_truncate(rec["summary"], 180) if rec["summary"] else "")
            room_info = f"Зал {rec['room_number']}" if rec.get("room_number") else "Зал: н/д"
            tags_str = ", ".join(rec.get("tags", [])[:3])
            entry = (
                f"*{rec['rank']}. {title}*\n"
                f"{summary}\n"
                f"📍 {room_info} · {tags_str}\n\n"
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


# --- Entry point ---


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /profile command."""
    tg_user = update.effective_user
    telegram_user_id = str(tg_user.id)

    auth = await _check_guest_or_business(telegram_user_id)
    if not auth:
        await update.message.reply_text(
            "Профилирование доступно только гостям и бизнес-партнёрам.\n"
            "Используйте /start для выбора роли."
        )
        return ConversationHandler.END

    user, event, role_code = auth
    context.user_data["profile_user_id"] = str(user.id)
    context.user_data["profile_event_id"] = str(event.id)

    # Check if profile already exists (T031 - US4)
    async with async_session() as session:
        profile = await profiling_service.get_or_create_profile(session, user.id, event.id)
        has_profile = bool(profile.selected_tags or profile.extracted_tags)

    if has_profile:
        interests = _format_interests(
            profile.selected_tags, profile.extracted_tags, profile.keywords
        )
        profile_text = f"Ваш текущий профиль: {interests}"
        if profile.extra_data and profile.extra_data.get("nl_summary"):
            profile_text += f"\n\n{profile.extra_data['nl_summary']}"
        profile_text += "\n\nОбновить?"
        await update.message.reply_text(
            profile_text,
            reply_markup=update_profile_keyboard(),
        )
        return CHOOSE_TAGS  # Will be handled by update_yes/no callbacks

    # New profile: start tag selection
    return await _start_tag_selection(update, context, is_callback=False)


async def start_profiling_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'start_profiling' callback from onboarding auto-trigger."""
    query = update.callback_query
    await query.answer()

    tg_user = query.from_user
    telegram_user_id = str(tg_user.id)

    auth = await _check_guest_or_business(telegram_user_id)
    if not auth:
        await query.edit_message_text("Профилирование доступно только гостям и бизнес-партнёрам.")
        return ConversationHandler.END

    user, event, _ = auth
    context.user_data["profile_user_id"] = str(user.id)
    context.user_data["profile_event_id"] = str(event.id)

    # Check if NL profiler already filled the profile — skip straight to generation
    has_tags = False
    async with async_session() as session:
        profile = await profiling_service.get_or_create_profile(session, user.id, event.id)
        if profile.selected_tags:
            context.user_data["profile_id"] = str(profile.id)
            has_tags = True

    if has_tags:
        return await _do_generate(update, context)

    # No tags yet — standard path via tag selection
    context.user_data["selected_tags"] = set()
    context.user_data["raw_text"] = None

    return await _start_tag_selection(update, context, is_callback=True)


async def _start_tag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool) -> int:
    """Show tag selection keyboard."""
    import uuid as _uuid
    event_id = _uuid.UUID(context.user_data["profile_event_id"])
    tags = await _load_tags(event_id)
    context.user_data["available_tags"] = tags

    selected = context.user_data.get("selected_tags", set())
    text = (
        "Выберите интересующие тематики (можно несколько).\n"
        "Или напишите текстом, что вас интересует."
    )

    if is_callback:
        query = update.callback_query
        await query.edit_message_text(
            text, reply_markup=tag_selection_keyboard(tags, selected)
        )
    else:
        await update.message.reply_text(
            text, reply_markup=tag_selection_keyboard(tags, selected)
        )

    return CHOOSE_TAGS


# --- CHOOSE_TAGS state ---


async def tag_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle tag toggle, 'done', or 'text' callbacks."""
    query = update.callback_query
    await query.answer()

    _, action = query.data.split(":", 1)

    if action == "_done":
        # Finalize tag selection
        selected = context.user_data.get("selected_tags", set())
        raw_text = context.user_data.get("raw_text")

        if not selected and not raw_text:
            await query.edit_message_text(
                "Укажите хотя бы один интерес — выберите тематику или напишите текстом.",
                reply_markup=tag_selection_keyboard(
                    context.user_data.get("available_tags", []), selected
                ),
            )
            return CHOOSE_TAGS

        return await _process_and_confirm(update, context)

    if action == "_text":
        await query.edit_message_text(
            "Напишите, что вас интересует (например: «антифрод в финтехе и hiring automation»).\n"
            "Или отправьте /skip чтобы пропустить."
        )
        return ENTER_TEXT

    # Toggle tag
    tag_name = action
    selected = context.user_data.get("selected_tags", set())
    if tag_name in selected:
        selected.discard(tag_name)
    else:
        selected.add(tag_name)
    context.user_data["selected_tags"] = selected

    tags = context.user_data.get("available_tags", [])
    await query.edit_message_reply_markup(
        reply_markup=tag_selection_keyboard(tags, selected)
    )
    return CHOOSE_TAGS


async def update_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle update_yes/update_no from existing profile prompt (T031)."""
    query = update.callback_query
    await query.answer()

    _, choice = query.data.split(":", 1)

    if choice == "update_no":
        await query.edit_message_text("Хорошо, профиль не изменён.")
        return ConversationHandler.END

    # update_yes — load previous selections and go to tag selection
    import uuid as _uuid
    user_id = _uuid.UUID(context.user_data["profile_user_id"])
    event_id = _uuid.UUID(context.user_data["profile_event_id"])

    async with async_session() as session:
        profile = await profiling_service.get_or_create_profile(session, user_id, event_id)
        context.user_data["selected_tags"] = set(profile.selected_tags)
        context.user_data["raw_text"] = None

    return await _start_tag_selection(update, context, is_callback=True)


async def free_text_in_tags(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle free text message in CHOOSE_TAGS state."""
    context.user_data["raw_text"] = update.message.text
    return await _process_and_confirm(update, context, is_message=True)


# --- ENTER_TEXT state ---


async def enter_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle text input in ENTER_TEXT state."""
    text = update.message.text
    if text.strip() == "/skip":
        context.user_data["raw_text"] = None
    else:
        context.user_data["raw_text"] = text
    return await _process_and_confirm(update, context, is_message=True)


# --- Process & Confirm ---


async def _process_and_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, is_message: bool = False) -> int:
    """Extract interests from text (if any), show confirmation."""
    selected = list(context.user_data.get("selected_tags", set()))
    raw_text = context.user_data.get("raw_text")
    available_tag_names = [t[0] for t in context.user_data.get("available_tags", [])]

    # Extract interests from text
    extracted_tags = []
    keywords = []
    if raw_text:
        result = await profiling_service.extract_interests_from_text(raw_text, available_tag_names)
        extracted_tags = result.get("tags", [])
        keywords = result.get("keywords", [])

        if not extracted_tags and not keywords and not selected:
            # AI extraction failed and no selected tags (T017)
            text = (
                "Не удалось определить интересы из текста.\n"
                "Попробуйте выбрать из списка тематик."
            )
            tags = context.user_data.get("available_tags", [])
            if is_message:
                await update.message.reply_text(
                    text, reply_markup=tag_selection_keyboard(tags, set(selected))
                )
            else:
                await update.callback_query.edit_message_text(
                    text, reply_markup=tag_selection_keyboard(tags, set(selected))
                )
            return CHOOSE_TAGS

        if not extracted_tags and not keywords and selected:
            # Text couldn't be processed but we have button selections (FR-003)
            notify = "Текст не удалось обработать, используем выбранные тематики."
            if is_message:
                await update.message.reply_text(notify)
            # Continue with just selected tags

    context.user_data["extracted_tags"] = extracted_tags
    context.user_data["keywords"] = keywords

    interests_text = _format_interests(selected, extracted_tags, keywords)
    confirm_text = f"Вас интересует: {interests_text}. Верно?"

    if is_message:
        await update.message.reply_text(
            confirm_text, reply_markup=confirm_interests_keyboard()
        )
    else:
        await update.callback_query.edit_message_text(
            confirm_text, reply_markup=confirm_interests_keyboard()
        )

    return CONFIRM_PROFILE


# --- CONFIRM_PROFILE state (T016) ---


async def confirm_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation: yes saves profile, no goes back to tags."""
    query = update.callback_query
    await query.answer()

    _, choice = query.data.split(":", 1)

    if choice == "no":
        # Return to tag selection with current selections preserved
        return await _start_tag_selection(update, context, is_callback=True)

    # Save profile
    import uuid as _uuid
    user_id = _uuid.UUID(context.user_data["profile_user_id"])
    event_id = _uuid.UUID(context.user_data["profile_event_id"])
    selected = list(context.user_data.get("selected_tags", set()))
    extracted = context.user_data.get("extracted_tags", [])
    all_tags = list(dict.fromkeys(selected + extracted))
    keywords = context.user_data.get("keywords", [])
    raw_text = context.user_data.get("raw_text")

    async with async_session() as session:
        profile = await profiling_service.get_or_create_profile(session, user_id, event_id)
        await profiling_service.save_profile(
            session, profile, all_tags, keywords, raw_text
        )
        context.user_data["profile_id"] = str(profile.id)

    logger.info("Profile confirmed: user=%s", user_id)
    await query.edit_message_text(
        "Профиль сохранён! Сгенерировать персональную программу?",
        reply_markup=generate_program_keyboard(),
    )
    return GENERATE_PROGRAM


# --- GENERATE_PROGRAM state (T022) ---


async def generate_program_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle generate/later callbacks."""
    query = update.callback_query
    await query.answer()

    _, choice = query.data.split(":", 1)

    if choice == "later":
        await query.edit_message_text(
            "Хорошо! Когда будете готовы, введите /profile и выберите «Сгенерировать программу»."
        )
        return ConversationHandler.END

    if choice == "generate":
        return await _do_generate(update, context)

    return GENERATE_PROGRAM


async def _do_generate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Run recommendation generation and display results."""
    import uuid as _uuid

    query = update.callback_query
    await query.edit_message_text("Генерирую персональную программу... ⏳")

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    user_id = _uuid.UUID(context.user_data["profile_user_id"])
    event_id = _uuid.UUID(context.user_data["profile_event_id"])

    async with async_session() as session:
        profile = await profiling_service.get_or_create_profile(session, user_id, event_id)
        data = await profiling_service.generate_recommendations(session, profile)

    if not data or data["total"] == 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Не удалось найти подходящие проекты. Попробуйте обновить профиль.",
            reply_markup=start_profiling_keyboard(),
        )
        return ConversationHandler.END

    context.user_data["recommendations"] = data
    return await _show_program(update, context)


async def _show_program(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Format and send recommendation messages (T022, T023, T025)."""
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

    return VIEW_PROGRAM


# --- VIEW_PROGRAM state ---


async def view_program_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle callbacks in VIEW_PROGRAM: detail, pagination, update."""
    query = update.callback_query
    await query.answer()

    data = query.data

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

    # Project detail (T028 - US3)
    if data.startswith("pdetail:"):
        pid_short = data.split(":")[1]
        return await _show_project_detail(update, context, pid_short)

    # Update profile (T032 - US4)
    if data == "profile:update":
        import uuid as _uuid
        user_id = _uuid.UUID(context.user_data["profile_user_id"])
        event_id = _uuid.UUID(context.user_data["profile_event_id"])

        async with async_session() as session:
            profile = await profiling_service.get_or_create_profile(session, user_id, event_id)
            context.user_data["selected_tags"] = set(profile.selected_tags)
            context.user_data["raw_text"] = None

        return await _start_tag_selection(update, context, is_callback=True)

    return VIEW_PROGRAM


async def view_program_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle text messages in VIEW_PROGRAM — LLM-powered Q&A about recommendations."""
    import json as _json
    from app.services import llm_client

    user_message = update.message.text
    recs_data = context.user_data.get("recommendations", {})

    # Build context about profile and recommendations
    profile_info = ""
    nl_summary = ""
    user_id = context.user_data.get("profile_user_id")
    event_id = context.user_data.get("profile_event_id")
    if user_id and event_id:
        import uuid as _uuid
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
        category = "must_visit" if rec.get("relevance_score", 0) >= 80 else "if_time"
        recs_summary += (
            f"#{rec['rank']} [{category}, score={rec.get('relevance_score', 0)}%] "
            f"{rec['title']} | tags={rec.get('tags', [])} | "
            f"Зал {rec.get('room_number', '?')} | "
            f"{(rec.get('summary') or '')[:200]}\n"
        )

    system_prompt = (
        "Ты — AI-куратор Demo Day. Пользователь уже получил персональную программу.\n"
        "Отвечай кратко (2-5 предложений), по делу, на русском языке.\n\n"
        "ТВОИ ВОЗМОЖНОСТИ:\n"
        "1. ПРОФИЛЬ — Покажи профиль пользователя по запросу (теги, ключевые слова, описание).\n"
        "2. Q&A-ПОМОЩНИК — Подготовь 3-5 умных вопросов к конкретному проекту из рекомендаций. "
        "Учитывай профиль пользователя и описание проекта. Вопросы должны быть конкретными, "
        "не общими.\n"
        "3. МАТРИЦА СРАВНЕНИЯ — Сравни 2-5 проектов в виде текстовой таблицы по критериям: "
        "тема, зал, релевантность, ключевые особенности. Используй простой текстовый формат.\n"
        "4. КОНТАКТ С АВТОРОМ — Объясни, что можно нажать кнопку «📞 Связаться с автором» "
        "в карточке проекта, автор получит запрос и решит, делиться ли контактом.\n"
        "5. МАРШРУТ — Помоги спланировать переходы между залами. "
        "Учитывай, что параллельные проекты в разных залах нельзя посетить одновременно.\n"
        "6. НАВИГАЦИЯ — Объясни, как пользоваться кнопками: "
        "номера проектов → детали, «Ещё рекомендации» → дополнительные, "
        "«Обновить профиль» → изменить интересы и пересгенерировать.\n\n"
        "Если просят что-то не связанное с Demo Day — мягко верни к теме.\n\n"
        f"ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:\n{profile_info}\n\n"
        f"РЕКОМЕНДАЦИИ ({len(all_recs)} проектов):\n{recs_summary}"
    )

    # Maintain conversation history in user_data
    chat_history = context.user_data.get("program_chat", [])
    chat_history.append({"role": "user", "content": user_message})
    # Keep last 10 exchanges to fit context
    if len(chat_history) > 20:
        chat_history = chat_history[-20:]

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    try:
        response = await llm_client.send_chat_completion(
            system_prompt=system_prompt,
            user_prompt="",
            messages=chat_history,
            json_mode=False,
        )
        reply = response if isinstance(response, str) else str(response)
    except Exception:
        logger.exception("LLM chat failed in VIEW_PROGRAM")
        reply = (
            f"Ваш профиль: {profile_info}\n"
            f"Рекомендаций: {len(all_recs)}\n\n"
            "Используйте кнопки выше для просмотра проектов."
        )

    chat_history.append({"role": "assistant", "content": reply})
    context.user_data["program_chat"] = chat_history

    await update.message.reply_text(reply)
    return VIEW_PROGRAM


# --- VIEW_DETAIL state (T028, T030) ---


async def _show_project_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, pid_short: str) -> int:
    """Show full project detail."""
    import uuid as _uuid

    query = update.callback_query
    profile_id = _uuid.UUID(context.user_data.get("profile_id", ""))

    # Find full project_id from recommendations
    recs_data = context.user_data.get("recommendations", {})
    all_recs = recs_data.get("must_visit", []) + recs_data.get("if_time", [])
    project_id = None
    for rec in all_recs:
        if rec["project_id"].startswith(pid_short):
            project_id = _uuid.UUID(rec["project_id"])
            break

    if not project_id:
        await query.edit_message_text("Проект не найден.")
        return VIEW_PROGRAM

    async with async_session() as session:
        detail = await profiling_service.get_project_detail(session, profile_id, project_id)

    if not detail:
        await query.edit_message_text("Проект не найден в подборке.")
        return VIEW_PROGRAM

    room_info = f"Зал {detail['room_number']}: {_escape_markdown(detail['room_name'])}" if detail.get("room_number") else "Зал: н/д"
    tags_str = ", ".join(detail.get("tags", []))
    score_pct = min(int(detail["relevance_score"]), 100) if detail["relevance_score"] > 0 else 0

    title = _escape_markdown(detail['title'])
    description = _escape_markdown(_truncate(detail['description'], 1500))
    author = _escape_markdown(detail.get('author', ''))
    telegram_contact = _escape_markdown(detail.get('telegram_contact', 'н/д'))

    text = (
        f"📋 *{title}*\n\n"
        f"{description}\n\n"
        f"🏷 Теги: {tags_str}\n"
        f"👤 Автор: {author}\n"
        f"📍 {room_info}\n"
        f"📱 Telegram: {telegram_contact}\n"
        f"📊 Релевантность: {score_pct}%"
    )

    if detail.get("llm_summary"):
        llm_summary = _escape_markdown(detail['llm_summary'])
        text += f"\n\n💡 *Кратко:* {llm_summary}"

    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup([
        [contact_button(project_id)],
        [InlineKeyboardButton("Назад к программе", callback_data="prof:back_program")],
    ])

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=keyboard,
    )
    return VIEW_DETAIL


async def back_to_program_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to program view from detail (T030)."""
    query = update.callback_query
    await query.answer()
    return await _show_program(update, context)


# --- Cancel ---


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Профилирование отменено.")
    return ConversationHandler.END


# --- Handler factory ---


def get_profiling_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("profile", profile_command),
            CallbackQueryHandler(start_profiling_callback, pattern=r"^start_profiling$"),
        ],
        states={
            CHOOSE_TAGS: [
                CallbackQueryHandler(tag_toggle_callback, pattern=r"^ptag:"),
                CallbackQueryHandler(update_profile_callback, pattern=r"^prof:update_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, free_text_in_tags),
            ],
            ENTER_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_text_handler),
                CommandHandler("skip", lambda u, c: _process_and_confirm(u, c, is_message=True)),
            ],
            CONFIRM_PROFILE: [
                CallbackQueryHandler(confirm_profile_callback, pattern=r"^prof:(yes|no)$"),
            ],
            GENERATE_PROGRAM: [
                CallbackQueryHandler(generate_program_callback, pattern=r"^prof:(generate|later)$"),
            ],
            VIEW_PROGRAM: [
                CallbackQueryHandler(view_program_callback, pattern=r"^(pdetail:|recpage:|profile:update|prof:show_if_time|noop)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, view_program_text),
            ],
            VIEW_DETAIL: [
                CallbackQueryHandler(back_to_program_callback, pattern=r"^prof:back_program$"),
                CallbackQueryHandler(contact_request_callback, pattern=r"^contact:req:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )
