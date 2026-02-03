"""Business Follow-up handlers for EPIC-015.

Commands:
  /bizfollowup — Business partner follow-up package with pipeline

Callbacks:
  bf:proj:{id}         — View project details
  bf:status:{id}:{s}   — Update status
  bf:loi:{id}          — Generate LOI
  bf:init              — Initialize pipeline from recommendations
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
from app.models.business_followup import PipelineStatus
from app.services import business_followup_service, user_service

logger = logging.getLogger(__name__)

# Conversation states
AWAITING_NOTES = 1


def pipeline_keyboard(followups: list) -> InlineKeyboardMarkup:
    """Create keyboard with pipeline projects."""
    buttons = []
    for f in followups[:8]:
        title = f.project.title[:25] + ".." if f.project and len(f.project.title) > 25 else (f.project.title if f.project else "Проект")
        buttons.append([InlineKeyboardButton(
            f"{f.status_emoji} {title}",
            callback_data=f"bf:proj:{f.id}"
        )])
    buttons.append([InlineKeyboardButton("🔄 Обновить", callback_data="bf:refresh")])
    return InlineKeyboardMarkup(buttons)


def project_detail_keyboard(followup_id: UUID) -> InlineKeyboardMarkup:
    """Create keyboard for project details."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📧 Contacted", callback_data=f"bf:status:{followup_id}:contacted"),
            InlineKeyboardButton("🤝 Negotiating", callback_data=f"bf:status:{followup_id}:negotiating"),
        ],
        [
            InlineKeyboardButton("✅ Won", callback_data=f"bf:status:{followup_id}:closed_won"),
            InlineKeyboardButton("❌ Lost", callback_data=f"bf:status:{followup_id}:closed_lost"),
        ],
        [InlineKeyboardButton("📝 Сгенерировать LOI", callback_data=f"bf:loi:{followup_id}")],
        [InlineKeyboardButton("📋 Добавить заметку", callback_data=f"bf:notes:{followup_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="bf:back")],
    ])


async def bizfollowup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bizfollowup command — show business pipeline."""
    async with async_session() as session:
        user = await user_service.get_user_by_telegram(
            session, str(update.effective_user.id)
        )
        if not user:
            await update.message.reply_text(
                "❌ Вы не зарегистрированы. Используйте /start"
            )
            return

        # Check if user has business profile
        profile = await business_followup_service.get_business_profile(session, user.id)
        if not profile:
            await update.message.reply_text(
                "❌ Business Follow-up доступен только для бизнес-партнёров.\n"
                "Пройдите бизнес-профилирование через /start"
            )
            return

        event = await user_service.get_current_event(session)
        if not event:
            await update.message.reply_text("❌ Нет текущего события.")
            return

        # Get or init pipeline
        followups = await business_followup_service.get_pipeline_projects(
            session, user.id, event.id
        )

        if not followups:
            # Try to init from recommendations
            added = await business_followup_service.init_pipeline_from_recommendations(
                session, user.id, event.id
            )
            await session.commit()

            if added > 0:
                followups = await business_followup_service.get_pipeline_projects(
                    session, user.id, event.id
                )
            else:
                await update.message.reply_text(
                    "📊 *Business Pipeline*\n\n"
                    "У вас пока нет проектов в работе.\n"
                    "Используйте /recommend для получения рекомендаций.",
                    parse_mode="Markdown",
                )
                return

        message = business_followup_service.format_pipeline_message(followups, profile)
        await update.message.reply_text(
            message,
            reply_markup=pipeline_keyboard(followups),
            parse_mode="Markdown",
        )


async def project_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show project details with action buttons."""
    query = update.callback_query
    await query.answer()

    followup_id = query.data.split(":")[-1]

    async with async_session() as session:
        from sqlalchemy import select
        from app.models.business_followup import BusinessFollowup
        from sqlalchemy.orm import selectinload

        result = await session.execute(
            select(BusinessFollowup)
            .options(selectinload(BusinessFollowup.project))
            .where(BusinessFollowup.id == UUID(followup_id))
        )
        followup = result.scalar_one_or_none()

        if not followup:
            await query.edit_message_text("❌ Проект не найден")
            return

        project = followup.project
        lines = [
            f"📋 *{project.title if project else 'Проект'}*\n",
            f"Статус: {followup.status_emoji} {followup.status.value}",
        ]

        if project and project.description:
            lines.append(f"\n_{project.description[:200]}_")

        if followup.notes:
            lines.append(f"\n📝 Заметки: {followup.notes}")

        if followup.loi_generated:
            lines.append("\n✅ LOI уже сгенерирован")

        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=project_detail_keyboard(UUID(followup_id)),
            parse_mode="Markdown",
        )


async def status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update project status."""
    query = update.callback_query
    await query.answer("Статус обновлён")

    parts = query.data.split(":")
    followup_id = parts[2]
    status_str = parts[3]

    status = PipelineStatus(status_str)

    async with async_session() as session:
        await business_followup_service.update_status(
            session, UUID(followup_id), status
        )
        await session.commit()

    # Refresh project view
    await project_detail_callback(update, context)


async def loi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate LOI for project."""
    query = update.callback_query
    await query.answer("Генерирую LOI...")

    followup_id = query.data.split(":")[-1]

    async with async_session() as session:
        from sqlalchemy import select
        from app.models.business_followup import BusinessFollowup

        result = await session.execute(
            select(BusinessFollowup).where(BusinessFollowup.id == UUID(followup_id))
        )
        followup = result.scalar_one_or_none()

        if not followup:
            await query.edit_message_text("❌ Проект не найден")
            return

        loi = await business_followup_service.generate_loi(
            session, followup.user_id, followup.project_id
        )
        await session.commit()

        if not loi:
            await query.edit_message_text(
                "❌ Не удалось сгенерировать LOI.\n"
                "Убедитесь, что заполнен бизнес-профиль."
            )
            return

        await query.edit_message_text(
            f"📝 *Letter of Intent*\n\n```\n{loi}\n```\n\n"
            "_Скопируйте и отправьте команде проекта_",
            parse_mode="Markdown",
        )


async def notes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start notes input."""
    query = update.callback_query
    await query.answer()

    followup_id = query.data.split(":")[-1]
    context.user_data["bf_notes_id"] = followup_id

    await query.edit_message_text(
        "📝 Напишите заметку к проекту:"
    )
    return AWAITING_NOTES


async def receive_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive notes text."""
    notes = update.message.text
    followup_id = context.user_data.get("bf_notes_id")

    if not followup_id:
        await update.message.reply_text("❌ Ошибка: проект не выбран")
        return ConversationHandler.END

    async with async_session() as session:
        await business_followup_service.add_notes(
            session, UUID(followup_id), notes
        )
        await session.commit()

    await update.message.reply_text(
        "✅ Заметка сохранена!\n\n"
        "Используйте /bizfollowup для просмотра pipeline."
    )
    return ConversationHandler.END


async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to pipeline view."""
    query = update.callback_query
    await query.answer()

    async with async_session() as session:
        user = await user_service.get_user_by_telegram(
            session, str(query.from_user.id)
        )
        if not user:
            await query.edit_message_text("❌ Пользователь не найден")
            return

        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("❌ Нет текущего события")
            return

        profile = await business_followup_service.get_business_profile(session, user.id)
        followups = await business_followup_service.get_pipeline_projects(
            session, user.id, event.id
        )

        message = business_followup_service.format_pipeline_message(followups, profile)
        await query.edit_message_text(
            message,
            reply_markup=pipeline_keyboard(followups),
            parse_mode="Markdown",
        )


async def refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refresh pipeline view."""
    await back_callback(update, context)


def get_business_followup_handlers() -> list:
    """Return list of handlers for EPIC-015."""
    notes_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(notes_callback, pattern=r"^bf:notes:"),
        ],
        states={
            AWAITING_NOTES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_notes),
            ],
        },
        fallbacks=[],
    )

    return [
        CommandHandler("bizfollowup", bizfollowup_command),
        CallbackQueryHandler(project_detail_callback, pattern=r"^bf:proj:"),
        CallbackQueryHandler(status_callback, pattern=r"^bf:status:"),
        CallbackQueryHandler(loi_callback, pattern=r"^bf:loi:"),
        CallbackQueryHandler(back_callback, pattern=r"^bf:back$"),
        CallbackQueryHandler(refresh_callback, pattern=r"^bf:refresh$"),
        notes_conv,
    ]
