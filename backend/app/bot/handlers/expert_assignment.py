"""Bot handlers for expert assignment: organizer matching wizard + expert invite flow."""

import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from app.bot.keyboards import (
    alternative_rooms_keyboard,
    approve_matching_confirm,
    coverage_dashboard_rooms,
    coverage_room_detail_keyboard,
    escalation_detail_keyboard,
    escalation_list_keyboard,
    expert_confirmed_keyboard,
    expert_invite_actions,
    expert_management_menu,
    invite_preview_keyboard,
    matching_result_rooms,
    move_target_room_keyboard,
    room_expert_detail_keyboard,
)
from app.config import settings
from app.database import async_session
from app.services import expert_service, matching_service, user_service

logger = logging.getLogger(__name__)

# Conversation states
(
    MENU,
    VIEW_MATCHING,
    ROOM_DETAIL,
    MOVE_SELECT_ROOM,
    APPROVE_CONFIRM,
    INVITE_PREVIEW,
    COVERAGE_DASHBOARD,
    COVERAGE_ROOM_DETAIL,
    ESCALATION_LIST,
    ESCALATION_DETAIL,
) = range(10)


def _is_organizer(user_id: int) -> bool:
    return str(user_id) in settings.organizer_ids


# ========== ORGANIZER: /experts command ==========


async def experts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: /experts command (organizer only)."""
    if not _is_organizer(update.effective_user.id):
        await update.message.reply_text("Эта команда доступна только организаторам.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Управление экспертами:",
        reply_markup=expert_management_menu(),
    )
    return MENU


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle main menu selections."""
    query = update.callback_query
    await query.answer()
    action = query.data.split(":")[1] if ":" in query.data else ""

    if action == "match":
        return await _run_matching(query, context)
    elif action == "coverage":
        return await _show_coverage(query, context)
    elif action == "invites":
        return await _show_invite_preview(query, context)
    elif action == "escalations":
        return await _show_escalations(query, context)
    elif action == "upload":
        await query.edit_message_text(
            "Загрузка экспертов: отправьте JSON-файл через API\n"
            "POST /api/v1/experts/upload"
        )
        return MENU
    elif action == "menu":
        await query.edit_message_text(
            "Управление экспертами:",
            reply_markup=expert_management_menu(),
        )
        return MENU
    elif action == "rematch":
        return await _run_matching(query, context)
    elif action == "approve_match":
        return await _show_approve_confirm(query, context)
    elif action == "back_rooms":
        return await _show_matching_result(query, context)
    elif action == "confirm_approve":
        return await _do_approve(query, context)
    elif action == "confirm_invite":
        return await _do_confirm_invites(query, context)
    elif action == "back_detail":
        # Go back to room detail — need room_id from context
        room_id = context.user_data.get("current_room_id")
        if room_id:
            return await _show_room_detail_by_id(query, context, room_id)
        return await _show_matching_result(query, context)

    return MENU


async def _run_matching(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Run matching algorithm."""
    from app.worker.tasks import run_matching_task
    from app.worker.utils import wait_for_task

    await query.edit_message_text("⏳ Запускаю матчинг экспертов по комнатам...")

    # Get event_id first
    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("Нет активного события.")
            return MENU
        event_id = str(event.id)

    # Submit to Celery
    task = run_matching_task.delay(event_id)

    # Wait for result
    completed, result = await wait_for_task(task.id, timeout=60, poll_interval=1.0)

    if not completed:
        await query.edit_message_text(
            "Матчинг занимает больше времени. Попробуйте позже."
        )
        return MENU

    if result is None:
        await query.edit_message_text("❌ Ошибка матчинга.")
        return MENU

    if "error" in result:
        await query.edit_message_text(f"Ошибка: {result['error']}")
        return MENU

    context.user_data["matching_result"] = result

    text = (
        f"✅ Матчинг завершён!\n\n"
        f"Всего экспертов: {result['total_experts']}\n"
        f"Распределено: {result['matched_experts']}\n"
        f"Без тегов: {result['unmatched_experts']}\n\n"
        f"Выберите зал для деталей:"
    )

    await query.edit_message_text(
        text,
        reply_markup=matching_result_rooms(result["rooms"]),
    )
    return VIEW_MATCHING


async def _show_matching_result(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show current matching result."""
    result = context.user_data.get("matching_result")
    if not result:
        async with async_session() as session:
            event = await user_service.get_current_event(session)
            if event:
                result = await matching_service.get_current_matching(session, event.id)
                context.user_data["matching_result"] = result

    if not result:
        await query.edit_message_text(
            "Нет результатов матчинга. Запустите матчинг первым.",
            reply_markup=expert_management_menu(),
        )
        return MENU

    text = (
        f"Текущее распределение:\n\n"
        f"Распределено: {result['matched_experts']} / {result['total_experts']}\n\n"
        f"Выберите зал:"
    )
    await query.edit_message_text(
        text,
        reply_markup=matching_result_rooms(result["rooms"]),
    )
    return VIEW_MATCHING


async def room_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle room selection from matching results."""
    query = update.callback_query
    await query.answer()

    room_id_prefix = query.data.split(":")[1] if ":" in query.data else ""
    return await _show_room_detail_by_id(query, context, room_id_prefix)


async def _show_room_detail_by_id(query, context, room_id_prefix: str) -> int:
    """Show experts in a specific room."""
    result = context.user_data.get("matching_result")
    if not result:
        await query.edit_message_text("Результат матчинга не найден.")
        return MENU

    room = None
    for r in result["rooms"]:
        if r["room_id"].startswith(room_id_prefix):
            room = r
            break

    if not room:
        await query.edit_message_text("Зал не найден.")
        return VIEW_MATCHING

    context.user_data["current_room_id"] = room_id_prefix
    context.user_data["current_room"] = room

    text = f"Зал: {room['room_name']}\nЭкспертов: {room['expert_count']}\n\n"
    for exp in room["experts"][:10]:
        tags = ", ".join(exp.get("matching_tags", [])[:3])
        manual = " (ручн.)" if exp.get("is_manual") else ""
        text += f"  {exp['name'][:30]} [{exp['match_score']:.1f}] {tags}{manual}\n"

    if room["expert_count"] > 10:
        text += f"\n... и ещё {room['expert_count'] - 10}"

    await query.edit_message_text(
        text,
        reply_markup=room_expert_detail_keyboard(room["experts"], room["room_id"]),
    )
    return ROOM_DETAIL


async def expert_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle expert selection for move."""
    query = update.callback_query
    await query.answer()

    expert_id_prefix = query.data.split(":")[1] if ":" in query.data else ""
    context.user_data["move_expert_prefix"] = expert_id_prefix

    result = context.user_data.get("matching_result")
    current_room = context.user_data.get("current_room", {})

    # Find expert's assignment ID
    for exp in current_room.get("experts", []):
        if exp["expert_id"].startswith(expert_id_prefix):
            context.user_data["move_expert_name"] = exp["name"]
            break

    await query.edit_message_text(
        "Перенести эксперта в другой зал.\nВыберите целевой зал:",
        reply_markup=move_target_room_keyboard(
            result["rooms"] if result else [],
            current_room.get("room_id", ""),
        ),
    )
    return MOVE_SELECT_ROOM


async def move_target_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle target room selection for move."""
    query = update.callback_query
    await query.answer()

    target_room_prefix = query.data.split(":")[1] if ":" in query.data else ""
    expert_prefix = context.user_data.get("move_expert_prefix", "")
    result = context.user_data.get("matching_result")

    if not result:
        await query.edit_message_text("Ошибка: нет данных матчинга.")
        return MENU

    # Find full IDs
    target_room_id = None
    for r in result["rooms"]:
        if r["room_id"].startswith(target_room_prefix):
            target_room_id = r["room_id"]
            break

    assignment_id = None
    current_room = context.user_data.get("current_room", {})

    # We need to find the assignment ID — query DB
    async with async_session() as session:
        from sqlalchemy import select

        from app.models.expert_room_assignment import ExpertRoomAssignment

        for exp in current_room.get("experts", []):
            if exp["expert_id"].startswith(expert_prefix):
                asgn_result = await session.execute(
                    select(ExpertRoomAssignment).where(
                        ExpertRoomAssignment.expert_id == exp["expert_id"]
                    ).where(
                        ExpertRoomAssignment.clustering_run_id == result["clustering_run_id"]
                    )
                )
                asgn = asgn_result.scalars().first()
                if asgn and target_room_id:
                    await matching_service.move_expert(session, asgn.id, target_room_id)
                    assignment_id = asgn.id
                break

    if assignment_id:
        expert_name = context.user_data.get("move_expert_name", "Эксперт")
        await query.edit_message_text(f"Эксперт {expert_name} перенесён.")
    else:
        await query.edit_message_text("Не удалось перенести эксперта.")

    # Refresh matching result
    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if event:
            result = await matching_service.get_current_matching(session, event.id)
            context.user_data["matching_result"] = result

    return await _show_matching_result(query, context)


async def _show_approve_confirm(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show approve confirmation."""
    result = context.user_data.get("matching_result", {})
    await query.edit_message_text(
        f"Утвердить распределение?\n"
        f"Экспертов: {result.get('matched_experts', 0)}\n"
        f"Залов: {len(result.get('rooms', []))}",
        reply_markup=approve_matching_confirm(),
    )
    return APPROVE_CONFIRM


async def _do_approve(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Actually approve matching."""
    result = context.user_data.get("matching_result", {})
    clustering_run_id = result.get("clustering_run_id")

    if not clustering_run_id:
        await query.edit_message_text("Нет матчинга для утверждения.")
        return MENU

    async with async_session() as session:
        count = await matching_service.approve_matching(session, clustering_run_id)

    await query.edit_message_text(
        f"Распределение утверждено! ({count} назначений)\n\n"
        f"Теперь можно отправить приглашения.",
        reply_markup=expert_management_menu(),
    )
    return MENU


# ========== INVITES ==========


async def _show_invite_preview(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show invite preview for organizer."""
    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("Нет активного события.")
            return MENU

        from app.services import invite_service
        preview = await invite_service.get_invite_preview(session, event.id)

    if not preview:
        await query.edit_message_text(
            "Нет утверждённого распределения. Сначала запустите и утвердите матчинг.",
            reply_markup=expert_management_menu(),
        )
        return MENU

    text = (
        f"Превью рассылки приглашений:\n\n"
        f"Всего экспертов: {preview['total_experts']}\n"
        f"С Telegram: {preview['with_telegram']}\n"
        f"Без Telegram: {preview['without_telegram']}\n\n"
        f"Пример сообщения:\n{preview['sample_message']}\n\n"
        f"Ссылка для чата: {preview['bot_link']}"
    )

    await query.edit_message_text(text, reply_markup=invite_preview_keyboard())
    return INVITE_PREVIEW


async def _do_confirm_invites(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm invite sending."""
    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("Нет активного события.")
            return MENU

        from app.services import invite_service
        result = await invite_service.confirm_invites(session, event.id)

    await query.edit_message_text(
        f"Приглашения подготовлены!\n\n"
        f"Экспертов: {result['invite_ready_count']}\n"
        f"Ссылка для чата экспертов:\n{result['bot_link']}\n\n"
        f"Отправьте эту ссылку в общий чат экспертов.",
        reply_markup=expert_management_menu(),
    )
    return MENU


# ========== COVERAGE ==========


async def _show_coverage(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show coverage dashboard."""
    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("Нет активного события.")
            return MENU

        from app.services import invite_service
        dashboard = await invite_service.get_coverage_dashboard(session, event.id)

    if not dashboard or not dashboard.get("rooms"):
        await query.edit_message_text(
            "Нет данных покрытия. Сначала запустите матчинг.",
            reply_markup=expert_management_menu(),
        )
        return MENU

    context.user_data["coverage"] = dashboard
    indicators = {"covered": "🟢", "partial": "🟡", "uncovered": "🔴"}

    text = "📊 Покрытие экспертами\n\n"
    for r in dashboard["rooms"]:
        ind = indicators.get(r["coverage_level"], "🔴")
        text += (
            f"{ind} {r['room_name'][:25]} — "
            f"{r['confirmed']}/{r['needed']} подтв. | "
            f"{r['declined']} отказ | "
            f"{r['no_response']} нет ответа\n"
        )

    totals = dashboard.get("totals", {})
    text += (
        f"\nИтого: {totals.get('confirmed', 0)}/{totals.get('total_needed', 0)} подтв. "
        f"({totals.get('coverage_percent', 0):.0f}%) | "
        f"{totals.get('declined', 0)} отказов | "
        f"{totals.get('no_response', 0)} нет ответа"
    )

    await query.edit_message_text(
        text,
        reply_markup=coverage_dashboard_rooms(dashboard["rooms"]),
    )
    return COVERAGE_DASHBOARD


async def coverage_room_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle room selection from coverage dashboard."""
    query = update.callback_query
    await query.answer()

    room_id_prefix = query.data.split(":")[1] if ":" in query.data else ""

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("Нет активного события.")
            return MENU

        from app.services import invite_service

        # Find full room_id
        dashboard = context.user_data.get("coverage", {})
        room_id = None
        room_name = ""
        for r in dashboard.get("rooms", []):
            if str(r["room_id"]).startswith(room_id_prefix):
                room_id = r["room_id"]
                room_name = r["room_name"]
                break

        if not room_id:
            await query.edit_message_text("Зал не найден.")
            return COVERAGE_DASHBOARD

        detail = await invite_service.get_room_coverage_detail(session, event.id, room_id)

    if not detail:
        await query.edit_message_text("Нет данных по этому залу.")
        return COVERAGE_DASHBOARD

    text = f"Зал: {room_name}\n\n"
    status_icons = {
        "confirmed": "✅", "declined": "❌", "invited": "📨",
        "invite_ready": "📋", "proposed": "📝", "approved": "✔️",
        "reassign_requested": "🔄", "no_show": "⚠️",
    }

    for exp in detail.get("experts", []):
        icon = status_icons.get(exp["status"], "❓")
        bot = "🤖" if exp["bot_started"] else ""
        text += f"  {icon} {exp['name'][:25]} [{exp['match_score']:.1f}] {bot}\n"

    suggested = detail.get("suggested_adjacent", [])
    if suggested:
        text += "\nПредлагаемые эксперты (смежные теги):\n"
        for s in suggested[:5]:
            tags = ", ".join(s.get("adjacent_tags", [])[:3])
            text += f"  💡 {s['name'][:25]} ({tags})\n"

    await query.edit_message_text(text, reply_markup=coverage_room_detail_keyboard())
    return COVERAGE_ROOM_DETAIL


# ========== ESCALATIONS ==========


async def _show_escalations(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show unresolved escalations."""
    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("Нет активного события.")
            return MENU

        from app.services import invite_service
        escalations = await invite_service.get_escalations(session, event.id)

    if not escalations:
        await query.edit_message_text(
            "Нет активных эскалаций.",
            reply_markup=expert_management_menu(),
        )
        return MENU

    context.user_data["escalations"] = escalations

    text = f"Эскалации ({len(escalations)}):\n\n"
    type_labels = {
        "no_response_reminder": "Нет ответа (3д)",
        "no_response_escalation": "Нет ответа (5д)",
        "room_uncovered": "Зал не покрыт",
        "room_partially_covered": "Частичное покрытие",
        "decline_impact": "Отказ с последствиями",
    }
    for esc in escalations[:10]:
        label = type_labels.get(esc["type"], esc["type"])
        text += f"  {label}: {esc['expert_name'][:20]} ({esc['room_name'][:15]})\n"

    await query.edit_message_text(
        text,
        reply_markup=escalation_list_keyboard(escalations),
    )
    return ESCALATION_LIST


async def escalation_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show escalation detail."""
    query = update.callback_query
    await query.answer()

    esc_id_prefix = query.data.split(":")[1] if ":" in query.data else ""
    escalations = context.user_data.get("escalations", [])

    esc = None
    for e in escalations:
        if str(e["id"]).startswith(esc_id_prefix):
            esc = e
            break

    if not esc:
        await query.edit_message_text("Эскалация не найдена.")
        return ESCALATION_LIST

    context.user_data["current_escalation_id"] = str(esc["id"])

    text = (
        f"Эскалация:\n\n"
        f"Тип: {esc['type']}\n"
        f"Эксперт: {esc['expert_name']}\n"
        f"Зал: {esc['room_name']}\n"
        f"Сообщение: {esc['message']}\n"
        f"Создано: {esc['created_at']}"
    )

    await query.edit_message_text(
        text,
        reply_markup=escalation_detail_keyboard(str(esc["id"])),
    )
    return ESCALATION_DETAIL


async def resolve_escalation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Resolve an escalation."""
    query = update.callback_query
    await query.answer()

    esc_id = context.user_data.get("current_escalation_id")
    if not esc_id:
        await query.edit_message_text("Ошибка.")
        return MENU

    async with async_session() as session:
        from app.services import invite_service
        await invite_service.resolve_escalation(session, esc_id)

    await query.edit_message_text("Эскалация разрешена.")
    return await _show_escalations(query, context)


# ========== EXPERT: /start expert handler ==========


async def handle_expert_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle expert coming to bot via t.me/bot?start=expert link."""
    tg_user = update.effective_user
    username = tg_user.username
    chat_id = str(update.effective_chat.id)

    if not username:
        await update.message.reply_text(
            "Для идентификации нужен Telegram-username. "
            "Установите username в настройках Telegram и попробуйте снова."
        )
        return ConversationHandler.END

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await update.message.reply_text("Нет активного события.")
            return ConversationHandler.END

        from app.services import invite_service
        result = await invite_service.handle_expert_start(session, event.id, username, chat_id)

    if not result:
        await update.message.reply_text(
            f"Вы не найдены в списке экспертов (username: @{username}).\n"
            f"Обратитесь к организатору."
        )
        return ConversationHandler.END

    expert = result["expert"]
    assignment = result.get("assignment")

    if not assignment:
        await update.message.reply_text(
            f"Здравствуйте, {expert['name']}!\n\n"
            f"Вы в списке экспертов, но распределение ещё не утверждено. "
            f"Мы сообщим, когда всё будет готово."
        )
        return ConversationHandler.END

    # Show personalized invite
    tags_text = ", ".join(expert.get("tags", [])[:5])
    text = (
        f"Здравствуйте, {expert['name']}!\n\n"
        f"Приглашаем на Demo Day!\n"
        f"По вашим интересам ({tags_text}) подходит:\n\n"
        f"🏛 {assignment['room_name']}\n"
        f"📊 {assignment.get('project_count', '?')} проектов\n\n"
        f"Что скажете?"
    )

    context.user_data["expert_assignment_id"] = assignment["id"]
    context.user_data["expert_name"] = expert["name"]

    await update.message.reply_text(text, reply_markup=expert_invite_actions())
    return ConversationHandler.END  # Callbacks handled separately


async def expert_invite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle expert invite response callbacks."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1] if ":" in query.data else ""

    # Try to find expert by username
    username = query.from_user.username
    if not username:
        await query.edit_message_text("Ошибка: не удалось определить username.")
        return

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("Нет активного события.")
            return

        from app.services import invite_service

        expert = await expert_service.get_expert_by_telegram(session, event.id, username)
        if not expert or not expert.assignments:
            await query.edit_message_text("Вы не найдены в списке экспертов.")
            return

        assignment = expert.assignments[0]

        if action == "confirm":
            await invite_service.confirm_attendance(session, assignment.id)
            room_name = assignment.room.name if assignment.room else "назначенный зал"
            await query.edit_message_text(
                f"Отлично! Вы записаны в: {room_name}\n\n"
                f"Ждём вас на Demo Day!",
                reply_markup=expert_confirmed_keyboard(),
            )

        elif action == "decline":
            await invite_service.decline_attendance(session, assignment.id)
            await query.edit_message_text(
                "Жаль, что не сможете! Если планы изменятся — напишите /start expert"
            )

        elif action == "reassign":
            rooms = await invite_service.request_reassignment(session, assignment.id)
            if rooms:
                await query.edit_message_text(
                    "Выберите комнату:",
                    reply_markup=alternative_rooms_keyboard(rooms),
                )
            else:
                await query.edit_message_text("Нет доступных альтернативных комнат.")

        elif action == "cancel_reassign":
            await query.edit_message_text(
                "Выберите действие:",
                reply_markup=expert_invite_actions(),
            )

        elif action == "change_room":
            rooms = await invite_service.request_reassignment(session, assignment.id)
            if rooms:
                await query.edit_message_text(
                    "Выберите новую комнату:",
                    reply_markup=alternative_rooms_keyboard(rooms),
                )
            else:
                await query.edit_message_text("Нет доступных альтернативных комнат.")


async def expert_room_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle expert choosing an alternative room."""
    query = update.callback_query
    await query.answer()

    room_id_prefix = query.data.split(":")[1] if ":" in query.data else ""
    username = query.from_user.username

    if not username:
        await query.edit_message_text("Ошибка.")
        return

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("Нет активного события.")
            return

        from app.services import invite_service

        expert = await expert_service.get_expert_by_telegram(session, event.id, username)
        if not expert or not expert.assignments:
            await query.edit_message_text("Ошибка.")
            return

        assignment = expert.assignments[0]

        # Find full room ID
        from sqlalchemy import select

        from app.models.room import Room
        rooms_result = await session.execute(select(Room))
        all_rooms = rooms_result.scalars().all()
        target_room = None
        for r in all_rooms:
            if str(r.id).startswith(room_id_prefix):
                target_room = r
                break

        if not target_room:
            await query.edit_message_text("Зал не найден.")
            return

        await invite_service.reassign_expert(session, assignment.id, target_room.id)

        await query.edit_message_text(
            f"Вы переназначены в: {target_room.name}\n\nЖдём вас на Demo Day!",
            reply_markup=expert_confirmed_keyboard(),
        )


async def noshow_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mark a confirmed expert as no-show."""
    query = update.callback_query
    await query.answer()

    expert_id_prefix = query.data.split(":")[1] if ":" in query.data else ""
    result = context.user_data.get("matching_result")
    current_room = context.user_data.get("current_room", {})

    if not result:
        await query.edit_message_text("Ошибка: нет данных матчинга.")
        return MENU

    async with async_session() as session:
        from sqlalchemy import select

        from app.models.expert_room_assignment import ExpertRoomAssignment
        from app.services import invite_service

        for exp in current_room.get("experts", []):
            if exp["expert_id"].startswith(expert_id_prefix):
                asgn_result = await session.execute(
                    select(ExpertRoomAssignment).where(
                        ExpertRoomAssignment.expert_id == exp["expert_id"]
                    ).where(
                        ExpertRoomAssignment.clustering_run_id == result["clustering_run_id"]
                    )
                )
                asgn = asgn_result.scalars().first()
                if asgn:
                    await invite_service.mark_no_show(session, asgn.id)
                    await query.edit_message_text(
                        f"Эксперт {exp['name']} отмечен как не пришедший."
                    )
                else:
                    await query.edit_message_text("Назначение не найдено.")
                break
        else:
            await query.edit_message_text("Эксперт не найден.")

    # Refresh and go back
    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if event:
            updated = await matching_service.get_current_matching(session, event.id)
            context.user_data["matching_result"] = updated

    return await _show_matching_result(query, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END


def get_expert_assignment_handler() -> ConversationHandler:
    """Organizer wizard for expert assignment management."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("experts", experts_command),
        ],
        states={
            MENU: [
                CallbackQueryHandler(menu_callback, pattern=r"^exp:"),
            ],
            VIEW_MATCHING: [
                CallbackQueryHandler(room_detail_callback, pattern=r"^mroom:"),
                CallbackQueryHandler(menu_callback, pattern=r"^exp:"),
            ],
            ROOM_DETAIL: [
                CallbackQueryHandler(expert_action_callback, pattern=r"^mexp:"),
                CallbackQueryHandler(noshow_callback, pattern=r"^noshow:"),
                CallbackQueryHandler(menu_callback, pattern=r"^exp:"),
                CallbackQueryHandler(room_detail_callback, pattern=r"^mpage:"),
            ],
            MOVE_SELECT_ROOM: [
                CallbackQueryHandler(move_target_callback, pattern=r"^mtarget:"),
                CallbackQueryHandler(menu_callback, pattern=r"^exp:"),
            ],
            APPROVE_CONFIRM: [
                CallbackQueryHandler(menu_callback, pattern=r"^exp:"),
            ],
            INVITE_PREVIEW: [
                CallbackQueryHandler(menu_callback, pattern=r"^exp:"),
            ],
            COVERAGE_DASHBOARD: [
                CallbackQueryHandler(coverage_room_callback, pattern=r"^croom:"),
                CallbackQueryHandler(menu_callback, pattern=r"^exp:"),
            ],
            COVERAGE_ROOM_DETAIL: [
                CallbackQueryHandler(menu_callback, pattern=r"^exp:"),
            ],
            ESCALATION_LIST: [
                CallbackQueryHandler(escalation_detail_callback, pattern=r"^esc:"),
                CallbackQueryHandler(menu_callback, pattern=r"^exp:"),
            ],
            ESCALATION_DETAIL: [
                CallbackQueryHandler(resolve_escalation_callback, pattern=r"^escr:"),
                CallbackQueryHandler(menu_callback, pattern=r"^exp:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
