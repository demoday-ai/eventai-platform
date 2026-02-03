"""Q&A Helper handlers for EPIC-009.

Commands:
  /questions — Get suggested questions for projects in your program
  /compare   — Compare projects side by side

Callbacks:
  qa:proj:{id}      — Select project for questions
  qa:more:{id}      — Generate more questions
  qa:back           — Back to project list
  cmp:sel:{id}      — Toggle project selection for comparison
  cmp:done          — Generate comparison matrix
  cmp:add           — Add custom criterion
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
from app.models.business_profile import BusinessProfile
from app.models.guest_profile import GuestProfile
from app.models.role import RoleCode
from app.models.user import User
from app.services import qa_service, user_service

logger = logging.getLogger(__name__)

# Conversation states
AWAITING_CRITERION = 1


async def _get_user_with_profiles(session, telegram_id: int) -> tuple[User | None, GuestProfile | None, BusinessProfile | None]:
    """Get user and their profiles."""
    user = await user_service.get_user_by_telegram_id(session, telegram_id)
    if not user:
        return None, None, None

    guest_profile = await user_service.get_guest_profile(session, user.id)
    business_profile = await user_service.get_business_profile(session, user.id)

    return user, guest_profile, business_profile


def _is_guest_or_business(user: User) -> bool:
    """Check if user is guest or business partner (not expert)."""
    # Experts should not use Q&A helper (per CustDev)
    if not user.roles:
        return False
    role_codes = [r.role.code for r in user.roles if r.role]
    return RoleCode.GUEST in role_codes or RoleCode.BUSINESS in role_codes


def project_list_keyboard(projects, prefix: str = "qa:proj") -> InlineKeyboardMarkup:
    """Create inline keyboard with project list."""
    buttons = []
    for project in projects[:10]:  # Limit to 10 projects
        title = project.title[:30] + "..." if len(project.title) > 30 else project.title
        buttons.append([InlineKeyboardButton(title, callback_data=f"{prefix}:{project.id}")])

    return InlineKeyboardMarkup(buttons)


def questions_keyboard(project_id: UUID) -> InlineKeyboardMarkup:
    """Keyboard for question display."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Ещё вопросы", callback_data=f"qa:more:{project_id}")],
        [InlineKeyboardButton("◀️ Другой проект", callback_data="qa:back")],
    ])


async def questions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /questions command."""
    async with async_session() as session:
        user, guest_profile, business_profile = await _get_user_with_profiles(
            session, update.effective_user.id
        )

        if not user:
            await update.message.reply_text(
                "❌ Пользователь не найден. Начните с /start"
            )
            return

        if not _is_guest_or_business(user):
            await update.message.reply_text(
                "ℹ️ Команда /questions доступна только для гостей и бизнес-партнёров.\n"
                "Эксперты формулируют вопросы самостоятельно."
            )
            return

        # Get recommended projects
        projects = await qa_service.get_user_recommendations(session, user.id)

        if not projects:
            await update.message.reply_text(
                "📋 У вас пока нет проектов в программе.\n"
                "Пройдите профилирование командой /profile, чтобы получить персональную подборку."
            )
            return

        # Store user_id in context for callbacks
        context.user_data["qa_user_id"] = str(user.id)
        context.user_data["qa_projects"] = {str(p.id): p.title for p in projects}

        await update.message.reply_text(
            f"❓ *Вопросы для Q&A*\n\n"
            f"У вас {len(projects)} проектов в программе.\n"
            f"Выберите проект, чтобы получить вопросы:",
            reply_markup=project_list_keyboard(projects),
            parse_mode="Markdown",
        )


async def project_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle project selection for questions."""
    query = update.callback_query
    await query.answer()

    # Parse project_id from callback data
    project_id = query.data.split(":")[-1]

    await query.edit_message_text("⏳ Генерирую вопросы...")

    async with async_session() as session:
        user, guest_profile, business_profile = await _get_user_with_profiles(
            session, query.from_user.id
        )

        if not user:
            await query.edit_message_text("❌ Ошибка: пользователь не найден")
            return

        # Get project
        from sqlalchemy import select
        from app.models.project import Project
        result = await session.execute(
            select(Project).where(Project.id == UUID(project_id))
        )
        project = result.scalar_one_or_none()

        if not project:
            await query.edit_message_text("❌ Проект не найден")
            return

        # Generate questions
        questions = await qa_service.generate_questions(
            session, user, project, guest_profile, business_profile
        )

        # Format response
        text = f"❓ *Вопросы для проекта:*\n_{project.title}_\n\n"
        for i, q in enumerate(questions, 1):
            text += f"{i}. {q}\n\n"

        await query.edit_message_text(
            text,
            reply_markup=questions_keyboard(project_id),
            parse_mode="Markdown",
        )


async def more_questions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'more questions' button."""
    query = update.callback_query
    await query.answer("Генерирую новые вопросы...")

    project_id = query.data.split(":")[-1]

    async with async_session() as session:
        user, guest_profile, business_profile = await _get_user_with_profiles(
            session, query.from_user.id
        )

        if not user:
            await query.edit_message_text("❌ Ошибка: пользователь не найден")
            return

        from sqlalchemy import select
        from app.models.project import Project
        result = await session.execute(
            select(Project).where(Project.id == UUID(project_id))
        )
        project = result.scalar_one_or_none()

        if not project:
            await query.edit_message_text("❌ Проект не найден")
            return

        # Delete cached questions to force regeneration
        from app.models.qa_suggestion import QASuggestion
        question_type = qa_service.get_question_type(user, business_profile)
        result = await session.execute(
            select(QASuggestion)
            .where(QASuggestion.user_id == user.id)
            .where(QASuggestion.project_id == project.id)
            .where(QASuggestion.question_type == question_type.value)
        )
        cached = result.scalar_one_or_none()
        if cached:
            await session.delete(cached)
            await session.commit()

        # Generate fresh questions
        questions = await qa_service.generate_questions(
            session, user, project, guest_profile, business_profile
        )

        text = f"❓ *Новые вопросы для проекта:*\n_{project.title}_\n\n"
        for i, q in enumerate(questions, 1):
            text += f"{i}. {q}\n\n"

        await query.edit_message_text(
            text,
            reply_markup=questions_keyboard(project_id),
            parse_mode="Markdown",
        )


async def back_to_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to project list."""
    query = update.callback_query
    await query.answer()

    async with async_session() as session:
        user, _, _ = await _get_user_with_profiles(session, query.from_user.id)

        if not user:
            await query.edit_message_text("❌ Ошибка: пользователь не найден")
            return

        projects = await qa_service.get_user_recommendations(session, user.id)

        if not projects:
            await query.edit_message_text("📋 Проектов нет. Используйте /profile")
            return

        await query.edit_message_text(
            f"❓ *Вопросы для Q&A*\n\n"
            f"Выберите проект:",
            reply_markup=project_list_keyboard(projects),
            parse_mode="Markdown",
        )


# Comparison matrix handlers

async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /compare command."""
    async with async_session() as session:
        user, guest_profile, business_profile = await _get_user_with_profiles(
            session, update.effective_user.id
        )

        if not user:
            await update.message.reply_text("❌ Пользователь не найден. Начните с /start")
            return

        if not _is_guest_or_business(user):
            await update.message.reply_text(
                "ℹ️ Команда /compare доступна только для гостей и бизнес-партнёров."
            )
            return

        projects = await qa_service.get_user_recommendations(session, user.id)

        if len(projects) < 2:
            await update.message.reply_text(
                "📋 Недостаточно проектов для сравнения (нужно минимум 2).\n"
                "Пройдите профилирование /profile"
            )
            return

        # Initialize selection
        context.user_data["cmp_selected"] = set()
        context.user_data["cmp_projects"] = {str(p.id): p.title for p in projects}

        await update.message.reply_text(
            f"📊 *Сравнение проектов*\n\n"
            f"Выберите 2-5 проектов для сравнения:",
            reply_markup=compare_project_keyboard(projects, set()),
            parse_mode="Markdown",
        )


def compare_project_keyboard(
    projects,
    selected: set[str],
) -> InlineKeyboardMarkup:
    """Create keyboard for project selection."""
    buttons = []
    for project in projects[:10]:
        pid = str(project.id)
        mark = "✅" if pid in selected else "⬜"
        title = project.title[:25] + "..." if len(project.title) > 25 else project.title
        buttons.append([
            InlineKeyboardButton(f"{mark} {title}", callback_data=f"cmp:sel:{pid}")
        ])

    # Add done button if 2+ selected
    if len(selected) >= 2:
        buttons.append([InlineKeyboardButton("📊 Сравнить", callback_data="cmp:done")])

    return InlineKeyboardMarkup(buttons)


async def compare_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle project selection toggle."""
    query = update.callback_query

    project_id = query.data.split(":")[-1]
    selected = context.user_data.get("cmp_selected", set())

    # Toggle selection
    if project_id in selected:
        selected.discard(project_id)
    elif len(selected) < 5:
        selected.add(project_id)
    else:
        await query.answer("Максимум 5 проектов")
        return

    context.user_data["cmp_selected"] = selected
    await query.answer()

    async with async_session() as session:
        user, _, _ = await _get_user_with_profiles(session, query.from_user.id)
        if not user:
            return

        projects = await qa_service.get_user_recommendations(session, user.id)

        await query.edit_message_text(
            f"📊 *Сравнение проектов*\n\n"
            f"Выбрано: {len(selected)} из 5\n"
            f"Выберите 2-5 проектов:",
            reply_markup=compare_project_keyboard(projects, selected),
            parse_mode="Markdown",
        )


async def compare_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and display comparison matrix."""
    query = update.callback_query
    await query.answer()

    selected = context.user_data.get("cmp_selected", set())
    if len(selected) < 2:
        await query.edit_message_text("❌ Выберите минимум 2 проекта")
        return

    await query.edit_message_text("⏳ Генерирую матрицу сравнения...")

    async with async_session() as session:
        user, _, business_profile = await _get_user_with_profiles(
            session, query.from_user.id
        )

        if not user:
            await query.edit_message_text("❌ Ошибка")
            return

        # Get selected projects
        from sqlalchemy import select
        from app.models.project import Project
        result = await session.execute(
            select(Project).where(Project.id.in_([UUID(pid) for pid in selected]))
        )
        projects = list(result.scalars().all())

        # Get criteria and generate matrix
        criteria = qa_service.get_default_criteria(user, business_profile)
        matrix = await qa_service.generate_comparison_matrix(session, projects, criteria)

        # Format and display
        text = qa_service.format_matrix_text(matrix, criteria)

        # Store for adding criteria
        context.user_data["cmp_matrix"] = matrix
        context.user_data["cmp_criteria"] = criteria

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Добавить критерий", callback_data="cmp:add")],
        ])

        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def add_criterion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start add criterion flow."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✏️ Введите название нового критерия для сравнения:"
    )
    return AWAITING_CRITERION


async def receive_criterion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive custom criterion from user."""
    criterion = update.message.text.strip()
    if not criterion:
        await update.message.reply_text("❌ Критерий не может быть пустым")
        return AWAITING_CRITERION

    criteria = context.user_data.get("cmp_criteria", [])
    criteria.append(criterion)
    context.user_data["cmp_criteria"] = criteria

    await update.message.reply_text(
        f"✅ Критерий '{criterion}' добавлен.\n"
        f"Для перегенерации матрицы используйте /compare заново."
    )
    return ConversationHandler.END


def get_qa_handlers() -> list:
    """Return list of handlers for EPIC-009."""
    return [
        CommandHandler("questions", questions_command),
        CommandHandler("compare", compare_command),
        CallbackQueryHandler(project_select_callback, pattern=r"^qa:proj:"),
        CallbackQueryHandler(more_questions_callback, pattern=r"^qa:more:"),
        CallbackQueryHandler(back_to_list_callback, pattern=r"^qa:back$"),
        CallbackQueryHandler(compare_select_callback, pattern=r"^cmp:sel:"),
        CallbackQueryHandler(compare_done_callback, pattern=r"^cmp:done$"),
        # Conversation for adding criterion
        ConversationHandler(
            entry_points=[
                CallbackQueryHandler(add_criterion_callback, pattern=r"^cmp:add$"),
            ],
            states={
                AWAITING_CRITERION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_criterion),
                ],
            },
            fallbacks=[],
        ),
    ]
