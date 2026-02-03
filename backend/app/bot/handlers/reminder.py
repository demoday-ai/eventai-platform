"""Reminder command handlers for EPIC-007: DD Reminders.

Commands:
  /remind — Organizer sends reminders to all roles

Callbacks:
  rem:type:day/hour  — Select reminder type
  rem:send:{id}      — Confirm and send
  rem:cancel         — Cancel reminder flow
  rem:resend:{id}    — Resend despite duplicate warning
"""

import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from app.bot.keyboards import (
    reminder_preview_keyboard,
    reminder_recovery_keyboard,
    reminder_resend_keyboard,
    reminder_type_keyboard,
)
from app.config import settings
from app.database import async_session
from app.models.reminder import ReminderType
from app.services import reminder_service, user_service

logger = logging.getLogger(__name__)


def _is_organizer(telegram_user_id: int | str) -> bool:
    """Check if user is an organizer."""
    return str(telegram_user_id) in settings.organizer_ids


# ---------------------------------------------------------------------------
# /remind command (T015)
# ---------------------------------------------------------------------------


async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /remind command - check for interrupted batch, then show type selection."""
    # T022: Check organizer access
    if not _is_organizer(update.effective_user.id):
        await update.message.reply_text("Команда доступна только организаторам.")
        return

    # T021: Check event exists within 2 days
    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await update.message.reply_text("Нет текущего события.")
            return

        days_until = (event.start_date - date.today()).days
        if days_until > 2:
            await update.message.reply_text(
                f"Нет события в ближайшие 2 дня.\n"
                f"Следующее событие: {event.start_date.strftime('%d.%m.%Y')} ({days_until} дней)"
            )
            return

        # EPIC-007b: Check for interrupted batch (T011)
        interrupted = await reminder_service.get_interrupted_batch(session, event.id)
        if interrupted:
            # Format time ago
            minutes_ago = int(
                (datetime.now(timezone.utc) - interrupted.started_at).total_seconds() / 60
            )
            if minutes_ago < 60:
                time_ago = f"{minutes_ago} мин. назад"
            else:
                hours = minutes_ago // 60
                time_ago = f"{hours} ч. назад"

            # Calculate progress
            sent = interrupted.sent_count or 0
            total = interrupted.total_recipients or 0
            reminder_type_label = (
                "за день" if interrupted.reminder_type.value == "day_before" else "за час"
            )

            await update.message.reply_text(
                f"⚠️ Обнаружена прерванная рассылка\n\n"
                f"Тип: Напоминания {reminder_type_label}\n"
                f"Начата: {time_ago}\n"
                f"Прогресс: {sent}/{total} отправлено\n\n"
                f"Что делать?",
                reply_markup=reminder_recovery_keyboard(str(interrupted.id)),
            )
            return

    await update.message.reply_text(
        "🔔 Напоминания Demo Day\n\n"
        "Выберите тип напоминания:",
        reply_markup=reminder_type_keyboard(),
    )


# ---------------------------------------------------------------------------
# Type selection callback (T016)
# ---------------------------------------------------------------------------


async def type_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reminder type selection (day/hour)."""
    query = update.callback_query
    await query.answer()

    if not _is_organizer(query.from_user.id):
        await query.edit_message_text("Команда доступна только организаторам.")
        return

    type_str = query.data.split(":")[2]  # rem:type:day or rem:type:hour
    reminder_type = ReminderType.DAY_BEFORE if type_str == "day" else ReminderType.HOUR_BEFORE
    type_label = "за день" if type_str == "day" else "за час"

    await query.edit_message_text(f"⏳ Загрузка превью напоминаний {type_label}...")

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("Нет текущего события.")
            return

        preview = await reminder_service.get_preview(session, event.id, reminder_type)

        # T017: Check for duplicate
        if preview.get("duplicate_warning"):
            dup = preview["duplicate_warning"]
            await query.edit_message_text(
                f"⚠️ Напоминания «{type_label}» уже отправлены {dup['minutes_ago']} мин. назад.\n"
                f"Отправлено: {dup['sent_count']}\n\n"
                f"Отправить повторно?",
                reply_markup=reminder_resend_keyboard(dup["batch_id"]),
            )
            # Store reminder type in context for resend
            context.user_data["reminder_type"] = reminder_type
            return

        # Format preview message
        students = preview["by_role"]["students"]
        experts = preview["by_role"]["experts"]
        guests = preview["by_role"]["guests"]
        business = preview["by_role"]["business"]

        lines = [
            f"📢 Напоминания {type_label} до Demo Day\n",
            f"📚 Студенты: {students['count']}",
        ]
        if students["skipped"]:
            lines[-1] += f" ({students['skipped']} без Telegram)"

        lines.append(f"🎓 Эксперты: {experts['count']}")
        if experts.get("skipped"):
            lines[-1] += f" ({experts['skipped']} без chat_id)"
        if experts.get("declined"):
            lines[-1] += f" ({experts['declined']} отклонили)"

        lines.append(f"👥 Гости: {guests['count']}")
        if guests["skipped"]:
            lines[-1] += f" ({guests['skipped']} без Telegram)"

        lines.append(f"💼 Бизнес: {business['count']}")
        if business["skipped"]:
            lines[-1] += f" ({business['skipped']} без Telegram)"

        lines.append(f"\n✉️ Итого: {preview['total_recipients']} получателей")
        if preview["total_skipped"]:
            lines.append(f"⏭️ Пропущено: {preview['total_skipped']}")

        text = "\n".join(lines)

        # Create batch in preview state to get ID
        batch = await reminder_service.create_batch(
            session,
            event.id,
            reminder_type,
            str(query.from_user.id),
            query.from_user.full_name,
            preview["total_recipients"],
        )
        await session.commit()

        await query.edit_message_text(
            text,
            reply_markup=reminder_preview_keyboard(str(batch.id)),
        )


# ---------------------------------------------------------------------------
# Send callback (T018)
# ---------------------------------------------------------------------------


async def send_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle send confirmation."""
    query = update.callback_query
    await query.answer()

    if not _is_organizer(query.from_user.id):
        await query.edit_message_text("Команда доступна только организаторам.")
        return

    batch_id_prefix = query.data.split(":")[2]  # rem:send:xxxxxxxx

    await query.edit_message_text("⏳ Отправка напоминаний...")

    async with async_session() as session:
        from sqlalchemy import select
        from app.models.reminder import ReminderBatch

        # Find batch by prefix
        result = await session.execute(
            select(ReminderBatch).where(
                ReminderBatch.id.cast(str).like(f"{batch_id_prefix}%")
            )
        )
        batch = result.scalars().first()
        if not batch:
            await query.edit_message_text("❌ Пакет рассылки не найден.")
            return

        event_id = batch.event_id

        # Execute batch
        import time
        start_time = time.time()

        batch = await reminder_service.execute_batch(session, batch, context.bot, event_id)

        elapsed = time.time() - start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        time_str = f"{minutes} мин {seconds} сек" if minutes else f"{seconds} сек"

        # Show report
        text = (
            f"✅ Рассылка завершена\n\n"
            f"Отправлено: {batch.sent_count}\n"
            f"Ошибки: {batch.failed_count}\n"
            f"Пропущено: {batch.skipped_count}\n\n"
            f"Время: {time_str}"
        )
        await query.edit_message_text(text)


# ---------------------------------------------------------------------------
# Cancel callback (T019)
# ---------------------------------------------------------------------------


async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancel."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Рассылка отменена.")


# ---------------------------------------------------------------------------
# Resend callback (T017 continuation)
# ---------------------------------------------------------------------------


async def resend_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle resend despite duplicate warning."""
    query = update.callback_query
    await query.answer()

    if not _is_organizer(query.from_user.id):
        await query.edit_message_text("Команда доступна только организаторам.")
        return

    # Get reminder type from context
    reminder_type = context.user_data.get("reminder_type", ReminderType.DAY_BEFORE)
    type_label = "за день" if reminder_type == ReminderType.DAY_BEFORE else "за час"

    await query.edit_message_text(f"⏳ Подготовка повторной рассылки {type_label}...")

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("Нет текущего события.")
            return

        preview = await reminder_service.get_preview(session, event.id, reminder_type)

        # Create new batch
        batch = await reminder_service.create_batch(
            session,
            event.id,
            reminder_type,
            str(query.from_user.id),
            query.from_user.full_name,
            preview["total_recipients"],
        )

        # Execute batch
        await query.edit_message_text("⏳ Отправка напоминаний...")

        import time
        start_time = time.time()

        batch = await reminder_service.execute_batch(session, batch, context.bot, event.id)

        elapsed = time.time() - start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        time_str = f"{minutes} мин {seconds} сек" if minutes else f"{seconds} сек"

        text = (
            f"✅ Повторная рассылка завершена\n\n"
            f"Отправлено: {batch.sent_count}\n"
            f"Ошибки: {batch.failed_count}\n"
            f"Пропущено: {batch.skipped_count}\n\n"
            f"Время: {time_str}"
        )
        await query.edit_message_text(text)


# ---------------------------------------------------------------------------
# Recovery callback (EPIC-007b T013-T016)
# ---------------------------------------------------------------------------


async def recovery_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle recovery choice: resume or start fresh."""
    query = update.callback_query
    await query.answer()

    if not _is_organizer(query.from_user.id):
        await query.edit_message_text("Команда доступна только организаторам.")
        return

    # Parse callback: rem:recover:resume:xxxxxxxx or rem:recover:fresh:xxxxxxxx
    parts = query.data.split(":")
    action = parts[2]  # resume or fresh
    batch_id_prefix = parts[3]

    async with async_session() as session:
        from sqlalchemy import select
        from app.models.reminder import ReminderBatch

        # Find batch by prefix
        result = await session.execute(
            select(ReminderBatch).where(
                ReminderBatch.id.cast(str).like(f"{batch_id_prefix}%")
            )
        )
        batch = result.scalars().first()
        if not batch:
            await query.edit_message_text("❌ Рассылка не найдена.")
            return

        if action == "resume":
            # T014: Resume the interrupted batch
            await query.edit_message_text("⏳ Возобновление рассылки...")

            import time
            start_time = time.time()

            batch = await reminder_service.resume_batch(session, batch, context.bot)

            elapsed = time.time() - start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            time_str = f"{minutes} мин {seconds} сек" if minutes else f"{seconds} сек"

            text = (
                f"✅ Рассылка возобновлена и завершена\n\n"
                f"Отправлено: {batch.sent_count}\n"
                f"Ошибки: {batch.failed_count}\n\n"
                f"Время: {time_str}"
            )
            await query.edit_message_text(text)

        elif action == "fresh":
            # T016: Cancel old batch, show type selection
            await reminder_service.cancel_batch(session, batch)

            await query.edit_message_text(
                "🔔 Предыдущая рассылка отменена.\n\n"
                "Выберите тип напоминания:",
                reply_markup=reminder_type_keyboard(),
            )


# ---------------------------------------------------------------------------
# Handler registration (T020)
# ---------------------------------------------------------------------------


def get_reminder_handlers() -> list:
    """Return list of handlers for EPIC-007 and EPIC-007b."""
    return [
        CommandHandler("remind", remind_command),
        CallbackQueryHandler(type_selection_callback, pattern=r"^rem:type:"),
        CallbackQueryHandler(send_callback, pattern=r"^rem:send:"),
        CallbackQueryHandler(cancel_callback, pattern=r"^rem:cancel$"),
        CallbackQueryHandler(resend_callback, pattern=r"^rem:resend:"),
        # EPIC-007b: Batch recovery
        CallbackQueryHandler(recovery_choice_callback, pattern=r"^rem:recover:"),
    ]
