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

from app.bot.utils import safe_send_long_message
from app.database import async_session
from app.services.core import user_service
from app.services.guest import followup_service

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
                "Сначала пройдите регистрацию через /start"
            )
            return

        # Check if user is a guest
        profile = await user_service.get_guest_profile(session, user.id)
        if not profile:
            await update.message.reply_text(
                "Сначала получите персональную программу через /start, "
                "чтобы сформировать follow-up пакет."
            )
            return

        event = await user_service.get_current_event(session)
        if not event:
            await update.message.reply_text(
                "Сейчас нет активных мероприятий."
            )
            return

        # Get or generate package
        package = await followup_service.get_or_create_package(
            session, user.id, event.id
        )
        await session.commit()

        # Format and send (may exceed 4096 chars with many projects)
        message = followup_service.format_package_message(package)
        await safe_send_long_message(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=refresh_keyboard(),
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
        # Use safe_send for potentially long messages (edit can't split)
        await safe_send_long_message(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=refresh_keyboard(),
        )


def get_followup_handlers() -> list:
    """Return list of handlers for EPIC-014."""
    return [
        CommandHandler("followup", followup_command),
        CallbackQueryHandler(refresh_callback, pattern=r"^fu:refresh$"),
    ]
