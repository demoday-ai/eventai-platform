"""Expert Scoring handlers for EPIC-013.

Commands:
  /score — Show unscored projects and start scoring

Callbacks:
  sc:proj:{id}       — Select project to score
  sc:crit:{crit}:{v} — Set criterion value
  sc:overall:{v}     — Set overall score
  sc:skip:{id}       — Skip (student didn't present)
  sc:comment:{id}    — Add comment
  sc:done:{id}       — Finish scoring
"""

import logging
from uuid import UUID

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.database import async_session
from app.services import scoring_service, user_service

logger = logging.getLogger(__name__)

# Conversation states
AWAITING_COMMENT = 1

CRITERIA_ORDER = ["relevance", "practical_value", "novelty", "implementation", "scalability", "research"]
CRITERIA_NAMES = {
    "relevance": "Актуальность",
    "practical_value": "Практ. значимость",
    "novelty": "Новизна",
    "implementation": "Реализация",
    "scalability": "Масштабируемость",
    "research": "R&D",
}


def project_list_keyboard(projects) -> InlineKeyboardMarkup:
    """Create keyboard with unscored projects."""
    buttons = []
    for p in projects[:15]:
        title = p.title[:28] + ".." if len(p.title) > 28 else p.title
        buttons.append([InlineKeyboardButton(title, callback_data=f"sc:proj:{p.id}")])
    return InlineKeyboardMarkup(buttons)


def criterion_keyboard(criterion: str, project_id: UUID) -> InlineKeyboardMarkup:
    """Create keyboard for scoring a criterion (1-3)."""
    name = CRITERIA_NAMES.get(criterion, criterion)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1️⃣", callback_data=f"sc:crit:{criterion}:1:{project_id}"),
            InlineKeyboardButton("2️⃣", callback_data=f"sc:crit:{criterion}:2:{project_id}"),
            InlineKeyboardButton("3️⃣", callback_data=f"sc:crit:{criterion}:3:{project_id}"),
        ],
        [
            InlineKeyboardButton("⏭️ Пропустить проект", callback_data=f"sc:skip:{project_id}"),
        ],
    ])


def overall_keyboard(project_id: UUID) -> InlineKeyboardMarkup:
    """Create keyboard for overall score (1-5)."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1", callback_data=f"sc:overall:1:{project_id}"),
            InlineKeyboardButton("2", callback_data=f"sc:overall:2:{project_id}"),
            InlineKeyboardButton("3", callback_data=f"sc:overall:3:{project_id}"),
            InlineKeyboardButton("4", callback_data=f"sc:overall:4:{project_id}"),
            InlineKeyboardButton("5", callback_data=f"sc:overall:5:{project_id}"),
        ],
    ])


def finish_keyboard(project_id: UUID) -> InlineKeyboardMarkup:
    """Keyboard after completing scores."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Добавить комментарий", callback_data=f"sc:comment:{project_id}")],
        [InlineKeyboardButton("✅ Готово", callback_data=f"sc:done:{project_id}")],
    ])


async def score_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /score command — show unscored projects."""
    async with async_session() as session:
        expert = await scoring_service.get_expert_by_telegram(
            session, str(update.effective_user.id)
        )
        if not expert:
            await update.message.reply_text(
                "❌ Вы не зарегистрированы как эксперт."
            )
            return

        event = await user_service.get_current_event(session)
        if not event:
            await update.message.reply_text("❌ Нет текущего события.")
            return

        projects = await scoring_service.get_projects_to_score(session, expert.id, event.id)
        summary = await scoring_service.get_expert_scores_summary(session, expert.id, event.id)

        if not projects:
            await update.message.reply_text(
                f"✅ *Оценка проектов*\n\n"
                f"Вы оценили все проекты!\n"
                f"Оценено: {summary['completed']}\n"
                f"Пропущено: {summary['skipped']}",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            f"📊 *Оценка проектов*\n\n"
            f"Не оценено: {len(projects)}\n"
            f"Оценено: {summary['completed']}\n\n"
            f"Выберите проект:",
            reply_markup=project_list_keyboard(projects),
            parse_mode="Markdown",
        )


async def project_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle project selection — start scoring flow."""
    query = update.callback_query
    await query.answer()

    project_id = query.data.split(":")[-1]
    context.user_data["sc_project_id"] = project_id
    context.user_data["sc_scores"] = {}
    context.user_data["sc_criterion_idx"] = 0

    async with async_session() as session:
        from sqlalchemy import select
        from app.models.project import Project
        result = await session.execute(
            select(Project).where(Project.id == UUID(project_id))
        )
        project = result.scalar_one_or_none()
        if not project:
            await query.edit_message_text("❌ Проект не найден")
            return

        context.user_data["sc_project_title"] = project.title

        # Start with first criterion
        criterion = CRITERIA_ORDER[0]
        name = CRITERIA_NAMES[criterion]

        await query.edit_message_text(
            f"📊 *Оценка проекта*\n"
            f"_{project.title}_\n\n"
            f"*{name}* (1-3):\n"
            f"1 = низко, 2 = средне, 3 = высоко",
            reply_markup=criterion_keyboard(criterion, UUID(project_id)),
            parse_mode="Markdown",
        )


async def criterion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle criterion score selection."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    criterion = parts[2]
    value = int(parts[3])
    project_id = parts[4]

    scores = context.user_data.get("sc_scores", {})
    scores[criterion] = value
    context.user_data["sc_scores"] = scores

    idx = context.user_data.get("sc_criterion_idx", 0) + 1
    context.user_data["sc_criterion_idx"] = idx

    project_title = context.user_data.get("sc_project_title", "Проект")

    if idx < len(CRITERIA_ORDER):
        # Next criterion
        next_crit = CRITERIA_ORDER[idx]
        name = CRITERIA_NAMES[next_crit]

        progress = scoring_service.format_score_criteria(scores, next_crit)

        await query.edit_message_text(
            f"📊 *Оценка проекта*\n"
            f"_{project_title}_\n\n"
            f"{progress}\n\n"
            f"*{name}* (1-3):",
            reply_markup=criterion_keyboard(next_crit, UUID(project_id)),
            parse_mode="Markdown",
        )
    else:
        # All criteria done, ask for overall
        progress = scoring_service.format_score_criteria(scores)

        await query.edit_message_text(
            f"📊 *Оценка проекта*\n"
            f"_{project_title}_\n\n"
            f"{progress}\n\n"
            f"*Общее впечатление* (1-5):",
            reply_markup=overall_keyboard(UUID(project_id)),
            parse_mode="Markdown",
        )


async def overall_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle overall score selection."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    value = int(parts[2])
    project_id = parts[3]

    scores = context.user_data.get("sc_scores", {})
    scores["overall"] = value
    context.user_data["sc_scores"] = scores

    # Save to database
    async with async_session() as session:
        expert = await scoring_service.get_expert_by_telegram(
            session, str(query.from_user.id)
        )
        if expert:
            await scoring_service.create_or_update_score(
                session, expert.id, UUID(project_id), scores
            )
            await session.commit()

    project_title = context.user_data.get("sc_project_title", "Проект")
    progress = scoring_service.format_score_criteria(scores)

    await query.edit_message_text(
        f"✅ *Оценка сохранена!*\n"
        f"_{project_title}_\n\n"
        f"{progress}\n"
        f"Общее: {value}/5\n\n"
        f"Хотите добавить комментарий?",
        reply_markup=finish_keyboard(UUID(project_id)),
        parse_mode="Markdown",
    )


async def skip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle skip (student didn't present)."""
    query = update.callback_query
    await query.answer()

    project_id = query.data.split(":")[-1]

    async with async_session() as session:
        expert = await scoring_service.get_expert_by_telegram(
            session, str(query.from_user.id)
        )
        if expert:
            await scoring_service.create_or_update_score(
                session, expert.id, UUID(project_id), {}, skipped=True
            )
            await session.commit()

    await query.edit_message_text(
        "⏭️ Проект пропущен (студент не выступил).\n\n"
        "Используйте /score для оценки следующего проекта."
    )


async def comment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start comment input."""
    query = update.callback_query
    await query.answer()

    project_id = query.data.split(":")[-1]
    context.user_data["sc_comment_project_id"] = project_id

    await query.edit_message_text(
        "💬 Напишите ваш комментарий к проекту:"
    )
    return AWAITING_COMMENT


async def receive_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive comment text."""
    comment = update.message.text
    project_id = context.user_data.get("sc_comment_project_id")

    if not project_id:
        await update.message.reply_text("❌ Ошибка: проект не выбран")
        return ConversationHandler.END

    async with async_session() as session:
        expert = await scoring_service.get_expert_by_telegram(
            session, str(update.effective_user.id)
        )
        if expert:
            await scoring_service.add_comment_to_score(
                session, expert.id, UUID(project_id), comment
            )

    await update.message.reply_text(
        "✅ Комментарий сохранён!\n\n"
        "Используйте /score для оценки следующего проекта."
    )
    return ConversationHandler.END


async def done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle done without comment."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "✅ Оценка завершена!\n\n"
        "Используйте /score для оценки следующего проекта."
    )


def get_scoring_handlers() -> list:
    """Return list of handlers for EPIC-013."""
    comment_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(comment_callback, pattern=r"^sc:comment:"),
        ],
        states={
            AWAITING_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_comment),
            ],
        },
        fallbacks=[],
    )

    return [
        CommandHandler("score", score_command),
        CallbackQueryHandler(project_select_callback, pattern=r"^sc:proj:"),
        CallbackQueryHandler(criterion_callback, pattern=r"^sc:crit:"),
        CallbackQueryHandler(overall_callback, pattern=r"^sc:overall:"),
        CallbackQueryHandler(skip_callback, pattern=r"^sc:skip:"),
        CallbackQueryHandler(done_callback, pattern=r"^sc:done:"),
        comment_conv,
    ]
