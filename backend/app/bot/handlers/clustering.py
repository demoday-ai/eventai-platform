"""Clustering wizard: upload → cluster → correct → approve.

ConversationHandler states:
- UPLOAD: Receive document (CSV/JSON) from organizer
- CONFIRM_REPLACE: Ask if replace existing projects
- CLUSTER_PARAMS: Select number of rooms
- CLUSTERING: Send typing, run LLM clustering
- VIEW_RESULT: Show rooms overview
- ROOM_DETAIL: Show projects in a room with pagination
- MOVE_SELECT_PROJECT: Select project to move
- MOVE_SELECT_ROOM: Select target room
- REGENERATE: Ask for NL feedback
- APPROVE_CONFIRM: Confirm approval
"""

import logging
import uuid

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
    approve_keyboard,
    confirm_replace_keyboard,
    project_list_keyboard,
    room_count_keyboard,
    room_detail_keyboard,
    rooms_overview_keyboard,
    target_room_keyboard,
)
from app.config import settings
from app.database import async_session
from app.services import clustering_service, project_service, user_service

logger = logging.getLogger(__name__)

# Conversation states
(
    UPLOAD,
    CONFIRM_REPLACE,
    CLUSTER_PARAMS,
    CLUSTERING,
    VIEW_RESULT,
    ROOM_DETAIL,
    MOVE_SELECT_PROJECT,
    MOVE_SELECT_ROOM,
    REGENERATE,
    APPROVE_CONFIRM,
) = range(10)


def _is_organizer(user_id: int) -> bool:
    return str(user_id) in settings.organizer_ids


async def clustering_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: /clustering command."""
    if not _is_organizer(update.effective_user.id):
        await update.message.reply_text("Эта команда доступна только организаторам.")
        return ConversationHandler.END

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await update.message.reply_text("Нет активного события.")
            return ConversationHandler.END

        context.user_data["event_id"] = str(event.id)
        count = await project_service.get_project_count(session, event.id)

    if count > 0:
        await update.message.reply_text(
            f"Загружено проектов: {count}\n\n"
            "Выберите действие:\n"
            "- Отправьте файл (CSV/JSON) для загрузки новых проектов\n"
            "- Нажмите кнопку для кластеризации",
            reply_markup=room_count_keyboard(count),
        )
        return CLUSTER_PARAMS

    await update.message.reply_text(
        "Проекты ещё не загружены.\n\n"
        "Отправьте файл с проектами (CSV или JSON).\n"
        "Обязательные поля: title, description, tags, author, telegram_contact"
    )
    return UPLOAD


async def receive_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle uploaded document."""
    if not _is_organizer(update.effective_user.id):
        return ConversationHandler.END

    document = update.message.document
    if not document:
        await update.message.reply_text("Отправьте файл (CSV или JSON).")
        return UPLOAD

    filename = (document.file_name or "").lower()
    if not filename.endswith((".csv", ".json")):
        await update.message.reply_text(
            "Поддерживаемые форматы: CSV, JSON\n"
            "Отправьте файл в правильном формате."
        )
        return UPLOAD

    # Download file
    file = await context.bot.get_file(document.file_id)
    content = await file.download_as_bytearray()

    # Parse
    try:
        if filename.endswith(".csv"):
            rows = project_service.parse_csv(bytes(content))
        else:
            rows = project_service.parse_json(bytes(content))
    except Exception as e:
        await update.message.reply_text(f"Ошибка парсинга: {e}")
        return UPLOAD

    if not rows:
        await update.message.reply_text("Файл не содержит данных.")
        return UPLOAD

    # Validate
    valid, errors, duplicate_titles = project_service.validate_rows(rows)

    # Store in context for later save
    context.user_data["upload_valid"] = valid
    context.user_data["upload_errors"] = errors
    context.user_data["upload_duplicates"] = duplicate_titles

    event_id = uuid.UUID(context.user_data["event_id"])

    async with async_session() as session:
        existing_count = await project_service.get_project_count(session, event_id)

    if existing_count > 0:
        context.user_data["existing_count"] = existing_count
        await update.message.reply_text(
            f"Найдено {len(valid)} валидных проектов.\n"
            f"Уже загружено: {existing_count} проектов.\n\n"
            f"Заменить данные?",
            reply_markup=confirm_replace_keyboard(),
        )
        return CONFIRM_REPLACE

    # No existing data, save directly
    return await _save_upload(update, context, replace=False)


async def confirm_replace_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle replace confirmation."""
    query = update.callback_query
    await query.answer()

    _, choice = query.data.split(":", 1)

    if choice == "no":
        await query.edit_message_text("Загрузка отменена. Отправьте другой файл или /cancel.")
        return UPLOAD

    return await _save_upload(update, context, replace=True)


async def _save_upload(update: Update, context: ContextTypes.DEFAULT_TYPE, replace: bool) -> int:
    """Save uploaded projects and transition to cluster params."""
    valid = context.user_data.pop("upload_valid", [])
    errors = context.user_data.pop("upload_errors", [])
    duplicate_titles = context.user_data.pop("upload_duplicates", [])
    event_id = uuid.UUID(context.user_data["event_id"])

    async with async_session() as session:
        if replace:
            await project_service.delete_all_projects(session, event_id)

        loaded = await project_service.save_projects(session, event_id, valid)

    # Build report
    report = f"Загружено: {loaded} проектов"
    if errors:
        report += f"\nОшибки: {len(errors)}"
        for e in errors[:5]:
            report += f"\n  строка {e.row}: {e.field} — {e.message}"
        if len(errors) > 5:
            report += f"\n  ...и ещё {len(errors) - 5}"
    if duplicate_titles:
        report += f"\nДубликаты: {len(duplicate_titles)}"

    target = update.callback_query if update.callback_query else update.message
    send = target.edit_message_text if update.callback_query else target.reply_text

    if loaded > 0:
        report += "\n\nТеперь можно запустить кластеризацию:"
        await send(report, reply_markup=room_count_keyboard(loaded))
        return CLUSTER_PARAMS

    await send(report + "\n\nОтправьте другой файл или /cancel.")
    return UPLOAD


async def cluster_params_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle room count selection."""
    query = update.callback_query
    await query.answer()

    _, num_str = query.data.split(":", 1)
    num_rooms = int(num_str)
    context.user_data["num_rooms"] = num_rooms

    await query.edit_message_text(f"Кластеризация на {num_rooms} залов... Подождите.")

    return await _run_clustering(update, context)


async def _run_clustering(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Execute clustering and show results."""
    from app.bot.keyboards import rooms_overview_keyboard_from_dict
    from app.worker.tasks import cluster_projects_task
    from app.worker.utils import wait_for_task

    event_id = context.user_data["event_id"]
    num_rooms = context.user_data.get("num_rooms", 6)
    feedback = context.user_data.pop("clustering_feedback", None)

    query = update.callback_query
    target = query if query else update.message
    send = target.edit_message_text if query else target.reply_text

    await send("⏳ Запускаю кластеризацию... Это может занять 1-2 минуты.")

    # Submit to Celery
    task = cluster_projects_task.delay(event_id, num_rooms, feedback)

    # Wait with longer timeout (clustering is heavy)
    completed, result = await wait_for_task(task.id, timeout=120, poll_interval=2.0)

    if not completed:
        # Task still running, save for later check
        context.user_data["pending_clustering_task"] = task.id
        await send(
            "Кластеризация занимает больше времени. "
            "Отправьте /status чтобы проверить готовность."
        )
        return CLUSTER_PARAMS

    if result is None:
        await send("❌ Ошибка кластеризации. Попробуйте снова или /cancel.")
        return CLUSTER_PARAMS

    # Build overview from result
    text = "✅ Кластеризация завершена!\n\n"
    text += f"Статус: {result['status']}\n"
    text += f"Залов: {result['num_rooms']}\n\n"

    for room in result["rooms"]:
        text += f"Зал {room['display_order'] + 1}: {room['name']} ({room['project_count']} проектов)\n"

    context.user_data["clustering_run_id"] = result["run_id"]

    await send(text, reply_markup=rooms_overview_keyboard_from_dict(result["rooms"]))
    return VIEW_RESULT


async def _render_room_detail(
    query, context: ContextTypes.DEFAULT_TYPE, room_id_str: str
) -> int:
    """Render room detail view (shared logic)."""
    room_id = uuid.UUID(room_id_str)
    page = context.user_data.get(f"room_page_{room_id_str}", 0)

    async with async_session() as session:
        room, projects = await clustering_service.get_room_details(session, room_id)

    if not room:
        await query.edit_message_text("Зал не найден.")
        return VIEW_RESULT

    page_size = 10
    start = page * page_size
    page_projects = projects[start:start + page_size]
    total_pages = (len(projects) + page_size - 1) // page_size

    text = f"Зал: {room.name}\n"
    text += f"Тема: {room.theme_rationale}\n"
    text += f"Проектов: {len(projects)}\n\n"

    for p in page_projects:
        tags_str = ""
        if p.tags:
            tag_names = [pt.tag.name for pt in p.tags if pt.tag]
            if tag_names:
                tags_str = f" [{', '.join(tag_names[:3])}]"
        text += f"• {p.title}{tags_str}\n"

    if total_pages > 1:
        text += f"\nСтраница {page + 1}/{total_pages}"

    context.user_data["current_room_id"] = room_id_str

    await query.edit_message_text(
        text,
        reply_markup=room_detail_keyboard(room_id, page, total_pages, len(projects)),
    )
    return ROOM_DETAIL


async def view_room_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show projects in a room."""
    query = update.callback_query
    await query.answer()

    _, room_id_str = query.data.split(":", 1)
    return await _render_room_detail(query, context, room_id_str)


async def room_page_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle pagination in room detail."""
    query = update.callback_query
    await query.answer()

    _, room_id_str, page_str = query.data.split(":", 2)
    context.user_data[f"room_page_{room_id_str}"] = int(page_str)

    return await _render_room_detail(query, context, room_id_str)


async def back_to_overview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Back to rooms overview."""
    query = update.callback_query
    await query.answer()

    run_id = uuid.UUID(context.user_data["clustering_run_id"])

    async with async_session() as session:
        run = await clustering_service.get_clustering_run(session, run_id)

    if not run:
        await query.edit_message_text("Кластеризация не найдена.")
        return ConversationHandler.END

    text = f"Кластеризация (статус: {run.status})\n\n"
    rooms_info = []
    for room in sorted(run.rooms, key=lambda r: r.display_order):
        proj_count = len(room.project_assignments)
        rooms_info.append((room, proj_count))
        text += f"Зал {room.display_order + 1}: {room.name} ({proj_count} проектов)\n"

    await query.edit_message_text(text, reply_markup=rooms_overview_keyboard(rooms_info))
    return VIEW_RESULT


async def move_select_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show project list for moving."""
    query = update.callback_query
    await query.answer()

    room_id_str = context.user_data.get("current_room_id")
    if not room_id_str:
        return VIEW_RESULT

    room_id = uuid.UUID(room_id_str)
    page = 0

    async with async_session() as session:
        room, projects = await clustering_service.get_room_details(session, room_id)

    if not projects:
        await query.edit_message_text("В зале нет проектов.")
        return VIEW_RESULT

    text = f"Выберите проект для переноса из зала «{room.name}»:"

    await query.edit_message_text(
        text,
        reply_markup=project_list_keyboard(projects, page),
    )
    return MOVE_SELECT_PROJECT


async def move_select_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show target rooms for move."""
    query = update.callback_query
    await query.answer()

    _, project_id_str = query.data.split(":", 1)
    context.user_data["move_project_id"] = project_id_str

    run_id = uuid.UUID(context.user_data["clustering_run_id"])
    current_room_id = uuid.UUID(context.user_data["current_room_id"])

    async with async_session() as session:
        run = await clustering_service.get_clustering_run(session, run_id)

    rooms = [(r, len(r.project_assignments)) for r in run.rooms if r.id != current_room_id]
    rooms.sort(key=lambda x: x[0].display_order)

    await query.edit_message_text(
        "Выберите зал для переноса:",
        reply_markup=target_room_keyboard(rooms),
    )
    return MOVE_SELECT_ROOM


async def move_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Execute project move."""
    query = update.callback_query
    await query.answer()

    _, target_room_id_str = query.data.split(":", 1)
    project_id = uuid.UUID(context.user_data["move_project_id"])
    target_room_id = uuid.UUID(target_room_id_str)
    run_id = uuid.UUID(context.user_data["clustering_run_id"])

    async with async_session() as session:
        await clustering_service.move_project(session, run_id, project_id, target_room_id)

    await query.edit_message_text("Проект перенесён!")

    # Return to overview
    return await back_to_overview(update, context)


async def regenerate_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for NL feedback before re-clustering."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "Опишите, что изменить в кластеризации:\n"
        "(например: «объедини NLP и Агентов в один зал» или «раздели EdTech на два зала»)"
    )
    return REGENERATE


async def regenerate_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Re-run clustering with user feedback."""
    feedback = update.message.text
    context.user_data["clustering_feedback"] = feedback

    await update.message.reply_text(f"Перегенерация с фидбэком: «{feedback}»\nПодождите...")

    return await _run_clustering(update, context)


async def approve_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm approval."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "Утвердить расписание?\n\n"
        "После утверждения расписание станет видимым для всех участников.",
        reply_markup=approve_keyboard(),
    )
    return APPROVE_CONFIRM


async def approve_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Execute approval."""
    query = update.callback_query
    await query.answer()

    _, choice = query.data.split(":", 1)

    if choice == "no":
        return await back_to_overview(update, context)

    run_id = uuid.UUID(context.user_data["clustering_run_id"])

    async with async_session() as session:
        result = await clustering_service.approve_clustering(session, run_id)

    if result == "already_approved":
        await query.edit_message_text(
            "Расписание уже было утверждено ранее.\n"
            "Для изменения запустите перегенерацию."
        )
        return VIEW_RESULT

    await query.edit_message_text("Расписание утверждено!")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the wizard."""
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END


async def upload_in_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle file upload during any wizard state."""
    return await receive_document(update, context)


def get_clustering_handler() -> ConversationHandler:
    """Build the clustering ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("clustering", clustering_command),
            CommandHandler("projects", clustering_command),
        ],
        states={
            UPLOAD: [
                MessageHandler(filters.Document.ALL, receive_document),
            ],
            CONFIRM_REPLACE: [
                CallbackQueryHandler(confirm_replace_handler, pattern=r"^replace:"),
            ],
            CLUSTER_PARAMS: [
                CallbackQueryHandler(cluster_params_handler, pattern=r"^rooms:"),
                MessageHandler(filters.Document.ALL, upload_in_wizard),
            ],
            VIEW_RESULT: [
                CallbackQueryHandler(view_room_detail, pattern=r"^room:"),
                CallbackQueryHandler(regenerate_prompt, pattern=r"^action:regenerate$"),
                CallbackQueryHandler(approve_prompt, pattern=r"^action:approve$"),
            ],
            ROOM_DETAIL: [
                CallbackQueryHandler(room_page_handler, pattern=r"^page:"),
                CallbackQueryHandler(back_to_overview, pattern=r"^action:back$"),
                CallbackQueryHandler(move_select_project, pattern=r"^action:move$"),
            ],
            MOVE_SELECT_PROJECT: [
                CallbackQueryHandler(move_select_target, pattern=r"^pick:"),
                CallbackQueryHandler(back_to_overview, pattern=r"^action:back$"),
            ],
            MOVE_SELECT_ROOM: [
                CallbackQueryHandler(move_execute, pattern=r"^target:"),
                CallbackQueryHandler(back_to_overview, pattern=r"^action:back$"),
            ],
            REGENERATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, regenerate_execute),
            ],
            APPROVE_CONFIRM: [
                CallbackQueryHandler(approve_execute, pattern=r"^approve:"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Document.ALL, upload_in_wizard),
        ],
    )
