"""Feedback moderation handlers for EPIC-012.

Commands:
  /feedback — Moderate expert feedback before sending to students

Callbacks:
  fb:proj:{id}     — Select project to review
  fb:item:{id}     — View feedback item
  fb:approve:{id}  — Approve feedback
  fb:reject:{id}   — Reject feedback
  fb:send:{id}     — Send all approved to student
  fb:back          — Back to project list
"""

import logging
from uuid import UUID

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from app.config import settings
from app.database import async_session
from app.services import feedback_service, user_service

logger = logging.getLogger(__name__)


def _is_organizer(telegram_user_id: int | str) -> bool:
    """Check if user is an organizer."""
    return str(telegram_user_id) in settings.organizer_ids


def project_list_keyboard(projects: list[dict]) -> InlineKeyboardMarkup:
    """Create keyboard with projects that have pending feedback."""
    buttons = []
    for p in projects[:15]:
        title = p["title"][:25] + "..." if len(p["title"]) > 25 else p["title"]
        buttons.append([
            InlineKeyboardButton(
                f"{title} ({p['pending_count']})",
                callback_data=f"fb:proj:{p['id']}"
            )
        ])
    return InlineKeyboardMarkup(buttons)


def feedback_review_keyboard(feedback_id: UUID, project_id: UUID) -> InlineKeyboardMarkup:
    """Keyboard for reviewing a single feedback item."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"fb:approve:{feedback_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"fb:reject:{feedback_id}"),
        ],
        [
            InlineKeyboardButton("📤 Отправить все студенту", callback_data=f"fb:send:{project_id}"),
        ],
        [
            InlineKeyboardButton("◀️ К проектам", callback_data="fb:back"),
        ],
    ])


async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /feedback command — show projects with pending feedback."""
    if not _is_organizer(update.effective_user.id):
        await update.message.reply_text("❌ Команда доступна только организаторам.")
        return

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await update.message.reply_text("❌ Нет текущего события.")
            return

        projects = await feedback_service.get_projects_with_pending_feedback(session, event.id)

        if not projects:
            await update.message.reply_text(
                "✅ *Модерация ОС*\n\n"
                "Нет проектов с непромодерированной обратной связью.",
                parse_mode="Markdown",
            )
            return

        total_pending = sum(p["pending_count"] for p in projects)
        await update.message.reply_text(
            f"📝 *Модерация обратной связи*\n\n"
            f"Проектов с ОС: {len(projects)}\n"
            f"Всего на модерации: {total_pending}\n\n"
            f"Выберите проект:",
            reply_markup=project_list_keyboard(projects),
            parse_mode="Markdown",
        )


async def project_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle project selection — show pending feedback."""
    query = update.callback_query
    await query.answer()

    if not _is_organizer(query.from_user.id):
        return

    project_id = query.data.split(":")[-1]
    context.user_data["fb_project_id"] = project_id

    async with async_session() as session:
        feedbacks = await feedback_service.get_pending_feedback_for_project(
            session, UUID(project_id)
        )

        if not feedbacks:
            await query.edit_message_text(
                "✅ Нет непромодерированной ОС для этого проекта."
            )
            return

        # Show first feedback
        fb = feedbacks[0]
        context.user_data["fb_index"] = 0
        context.user_data["fb_count"] = len(feedbacks)

        text = format_feedback_review(fb, 1, len(feedbacks))
        await query.edit_message_text(
            text,
            reply_markup=feedback_review_keyboard(fb.id, UUID(project_id)),
            parse_mode="Markdown",
        )


def format_feedback_review(fb, index: int, total: int) -> str:
    """Format feedback for review."""
    category_map = {
        "technical": "🔧 Техническое",
        "product": "💡 Продукт",
        "presentation": "🎤 Презентация",
        "general": "📋 Общее",
    }
    cat = category_map.get(fb.category, "📋 Общее")
    constructive = "✅ Конструктивно" if fb.is_constructive else "⚠️ Требует внимания"

    lines = [
        f"📝 *Отзыв {index}/{total}*",
        "",
        f"*Эксперт:* {fb.expert.name if fb.expert else 'Неизвестен'}",
        f"*Категория:* {cat}",
        f"*Оценка AI:* {constructive}",
        "",
        "*Оригинал:*",
        f"_{fb.original_text[:300]}{'...' if len(fb.original_text) > 300 else ''}_",
        "",
        "*AI-версия:*",
        fb.processed_text or "(не обработано)",
    ]
    return "\n".join(lines)


async def approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle feedback approval."""
    query = update.callback_query
    await query.answer("✅ Одобрено")

    if not _is_organizer(query.from_user.id):
        return

    feedback_id = query.data.split(":")[-1]
    project_id = context.user_data.get("fb_project_id")

    async with async_session() as session:
        await feedback_service.approve_feedback(session, UUID(feedback_id))

        # Show next feedback or completion
        if project_id:
            feedbacks = await feedback_service.get_pending_feedback_for_project(
                session, UUID(project_id)
            )
            if feedbacks:
                fb = feedbacks[0]
                text = format_feedback_review(fb, 1, len(feedbacks))
                await query.edit_message_text(
                    text,
                    reply_markup=feedback_review_keyboard(fb.id, UUID(project_id)),
                    parse_mode="Markdown",
                )
            else:
                await query.edit_message_text(
                    "✅ Все отзывы промодерированы!\n\n"
                    "Нажмите 'Отправить студенту' чтобы отправить одобренные отзывы.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Отправить студенту", callback_data=f"fb:send:{project_id}")],
                        [InlineKeyboardButton("◀️ К проектам", callback_data="fb:back")],
                    ]),
                )


async def reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle feedback rejection."""
    query = update.callback_query
    await query.answer("❌ Отклонено")

    if not _is_organizer(query.from_user.id):
        return

    feedback_id = query.data.split(":")[-1]
    project_id = context.user_data.get("fb_project_id")

    async with async_session() as session:
        await feedback_service.reject_feedback(session, UUID(feedback_id))

        # Show next or completion
        if project_id:
            feedbacks = await feedback_service.get_pending_feedback_for_project(
                session, UUID(project_id)
            )
            if feedbacks:
                fb = feedbacks[0]
                text = format_feedback_review(fb, 1, len(feedbacks))
                await query.edit_message_text(
                    text,
                    reply_markup=feedback_review_keyboard(fb.id, UUID(project_id)),
                    parse_mode="Markdown",
                )
            else:
                await query.edit_message_text(
                    "✅ Все отзывы промодерированы!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Отправить студенту", callback_data=f"fb:send:{project_id}")],
                        [InlineKeyboardButton("◀️ К проектам", callback_data="fb:back")],
                    ]),
                )


async def send_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle send to student."""
    query = update.callback_query
    await query.answer("Отправляю...")

    if not _is_organizer(query.from_user.id):
        return

    project_id = query.data.split(":")[-1]

    async with async_session() as session:
        count = await feedback_service.send_feedback_to_student(
            session, UUID(project_id), context.bot
        )

        if count > 0:
            await query.edit_message_text(
                f"✅ Отправлено {count} отзывов студенту!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ К проектам", callback_data="fb:back")],
                ]),
            )
        else:
            await query.edit_message_text(
                "⚠️ Нет одобренных отзывов для отправки или студент не найден.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ К проектам", callback_data="fb:back")],
                ]),
            )


async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to project list."""
    query = update.callback_query
    await query.answer()

    if not _is_organizer(query.from_user.id):
        return

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("❌ Нет события.")
            return

        projects = await feedback_service.get_projects_with_pending_feedback(session, event.id)

        if not projects:
            await query.edit_message_text(
                "✅ Нет проектов с непромодерированной ОС."
            )
            return

        total_pending = sum(p["pending_count"] for p in projects)
        await query.edit_message_text(
            f"📝 *Модерация обратной связи*\n\n"
            f"Проектов: {len(projects)}\n"
            f"На модерации: {total_pending}\n\n"
            f"Выберите проект:",
            reply_markup=project_list_keyboard(projects),
            parse_mode="Markdown",
        )


def get_feedback_handlers() -> list:
    """Return list of handlers for EPIC-012."""
    return [
        CommandHandler("feedback", feedback_command),
        CallbackQueryHandler(project_select_callback, pattern=r"^fb:proj:"),
        CallbackQueryHandler(approve_callback, pattern=r"^fb:approve:"),
        CallbackQueryHandler(reject_callback, pattern=r"^fb:reject:"),
        CallbackQueryHandler(send_callback, pattern=r"^fb:send:"),
        CallbackQueryHandler(back_callback, pattern=r"^fb:back$"),
    ]
