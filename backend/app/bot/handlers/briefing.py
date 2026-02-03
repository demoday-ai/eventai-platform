"""Briefing command handlers for EPIC-008: Expert Project Overview.

Commands:
  /briefing — Organizer sends project briefings to experts

Callbacks:
  brief:send      — Confirm and send briefings
  brief:cancel    — Cancel briefing flow
"""

import logging
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from app.config import settings
from app.database import async_session
from app.services import briefing_service, user_service

logger = logging.getLogger(__name__)


def _is_organizer(telegram_user_id: int | str) -> bool:
    """Check if user is an organizer."""
    return str(telegram_user_id) in settings.organizer_ids


def briefing_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm send or cancel."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Отправить брифинги", callback_data="brief:send")],
        [InlineKeyboardButton("❌ Отмена", callback_data="brief:cancel")],
    ])


async def briefing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /briefing command - show preview and confirm."""
    if not _is_organizer(update.effective_user.id):
        await update.message.reply_text("Команда доступна только организаторам.")
        return

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await update.message.reply_text("Нет текущего события.")
            return

        preview = await briefing_service.get_briefing_preview(session, event.id)

        if preview.get("error"):
            await update.message.reply_text(f"❌ {preview['error']}")
            return

        text = (
            f"📋 Брифинг экспертов\n\n"
            f"Экспертов (confirmed): {preview['expert_count']}\n"
            f"С Telegram: {preview['with_telegram']}\n"
            f"Без Telegram: {preview['without_telegram']}\n\n"
            f"Отправить брифинги с карточками проектов?"
        )

        await update.message.reply_text(
            text,
            reply_markup=briefing_confirm_keyboard(),
        )


async def send_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle send confirmation."""
    query = update.callback_query
    await query.answer()

    if not _is_organizer(query.from_user.id):
        await query.edit_message_text("Команда доступна только организаторам.")
        return

    await query.edit_message_text("⏳ Отправка брифингов...")

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("❌ Нет текущего события.")
            return

        start_time = time.time()

        result = await briefing_service.send_all_briefings(session, event.id, context.bot)

        elapsed = time.time() - start_time
        seconds = int(elapsed)

        text = (
            f"✅ Брифинги отправлены\n\n"
            f"Отправлено: {result['sent']}\n"
            f"Ошибки: {result['failed']}\n"
            f"Пропущено: {result['skipped']}\n\n"
            f"Время: {seconds} сек"
        )
        await query.edit_message_text(text)


async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancel."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Рассылка брифингов отменена.")


def get_briefing_handlers() -> list:
    """Return list of handlers for EPIC-008."""
    return [
        CommandHandler("briefing", briefing_command),
        CallbackQueryHandler(send_callback, pattern=r"^brief:send$"),
        CallbackQueryHandler(cancel_callback, pattern=r"^brief:cancel$"),
    ]
