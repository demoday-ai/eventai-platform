"""Guest Follow-up handlers for EPIC-014.

Commands:
  /followup — Get personal follow-up package after Demo Day

Callbacks:
  fu:refresh — Regenerate package with latest data
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from app.database import async_session
from app.services import followup_service, user_service

logger = logging.getLogger(__name__)


def refresh_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard with refresh option."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Обновить", callback_data="fu:refresh")],
    ])


async def followup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /followup command — get personal follow-up package."""
    async with async_session() as session:
        user = await user_service.get_user_by_telegram(
            session, str(update.effective_user.id)
        )
        if not user:
            await update.message.reply_text(
                "❌ Вы не зарегистрированы. Используйте /start"
            )
            return

        # Check if user is a guest
        profile = await user_service.get_guest_profile(session, user.id)
        if not profile:
            await update.message.reply_text(
                "❌ Follow-up пакет доступен только для гостей.\n"
                "Пройдите профилирование через /start"
            )
            return

        event = await user_service.get_current_event(session)
        if not event:
            await update.message.reply_text("❌ Нет текущего события.")
            return

        # Get or generate package
        package = await followup_service.get_or_create_package(
            session, user.id, event.id
        )
        await session.commit()

        # Format and send
        message = followup_service.format_package_message(package)
        await update.message.reply_text(
            message,
            reply_markup=refresh_keyboard(),
            parse_mode="Markdown",
        )


async def refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle package refresh."""
    query = update.callback_query
    await query.answer("Обновляю...")

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

        # Regenerate package
        package = await followup_service.get_or_create_package(
            session, user.id, event.id, force_regenerate=True
        )
        await session.commit()

        message = followup_service.format_package_message(package)
        await query.edit_message_text(
            message,
            reply_markup=refresh_keyboard(),
            parse_mode="Markdown",
        )


def get_followup_handlers() -> list:
    """Return list of handlers for EPIC-014."""
    return [
        CommandHandler("followup", followup_command),
        CallbackQueryHandler(refresh_callback, pattern=r"^fu:refresh$"),
    ]
