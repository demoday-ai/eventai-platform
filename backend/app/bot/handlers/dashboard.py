"""Organizer Dashboard handlers for EPIC-011.

Commands:
  /dashboard — Show real-time Demo Day status

Callbacks:
  dash:refresh  — Refresh dashboard
  dash:noshows  — Show no-show students
  dash:problems — Show rooms without experts
  dash:guests   — Show guest breakdown
  dash:back     — Back to main dashboard
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from app.config import settings
from app.database import async_session
from app.services import dashboard_service, user_service

logger = logging.getLogger(__name__)


def _is_organizer(telegram_user_id: int | str) -> bool:
    """Check if user is an organizer."""
    return str(telegram_user_id) in settings.organizer_ids


def dashboard_keyboard() -> InlineKeyboardMarkup:
    """Main dashboard action buttons."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Обновить", callback_data="dash:refresh"),
        ],
        [
            InlineKeyboardButton("📋 Неявки", callback_data="dash:noshows"),
            InlineKeyboardButton("⚠️ Проблемы", callback_data="dash:problems"),
        ],
        [
            InlineKeyboardButton("👥 Гости", callback_data="dash:guests"),
        ],
    ])


def back_keyboard() -> InlineKeyboardMarkup:
    """Back to dashboard button."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data="dash:back")],
    ])


async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dashboard command."""
    if not _is_organizer(update.effective_user.id):
        await update.message.reply_text("❌ Команда доступна только организаторам.")
        return

    await update.message.reply_text("⏳ Загрузка дашборда...")

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await update.message.reply_text("❌ Нет текущего события.")
            return

        # Gather stats
        student_stats = await dashboard_service.get_student_stats(session, event.id)
        expert_stats = await dashboard_service.get_expert_stats(session, event.id)
        guest_stats = await dashboard_service.get_guest_stats(session, event.id)
        alerts = dashboard_service.get_alerts(student_stats, expert_stats)

        # Format and send
        text = dashboard_service.format_dashboard(
            student_stats, expert_stats, guest_stats, alerts,
            event_name=event.name or "Demo Day"
        )

        await update.message.reply_text(
            text,
            reply_markup=dashboard_keyboard(),
            parse_mode="Markdown",
        )


async def refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle dashboard refresh."""
    query = update.callback_query
    await query.answer("Обновляю...")

    if not _is_organizer(query.from_user.id):
        await query.edit_message_text("❌ Доступ запрещён.")
        return

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("❌ Нет текущего события.")
            return

        student_stats = await dashboard_service.get_student_stats(session, event.id)
        expert_stats = await dashboard_service.get_expert_stats(session, event.id)
        guest_stats = await dashboard_service.get_guest_stats(session, event.id)
        alerts = dashboard_service.get_alerts(student_stats, expert_stats)

        text = dashboard_service.format_dashboard(
            student_stats, expert_stats, guest_stats, alerts,
            event_name=event.name or "Demo Day"
        )

        await query.edit_message_text(
            text,
            reply_markup=dashboard_keyboard(),
            parse_mode="Markdown",
        )


async def noshows_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle no-shows list request."""
    query = update.callback_query
    await query.answer()

    if not _is_organizer(query.from_user.id):
        return

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("❌ Нет события.")
            return

        no_shows = await dashboard_service.get_no_show_list(session, event.id)

        if not no_shows:
            text = "✅ *Нет отказов*\n\nВсе студенты подтвердили участие."
        else:
            text = f"📋 *Отказавшиеся студенты ({len(no_shows)})*\n\n"
            for i, ns in enumerate(no_shows[:20], 1):  # Limit to 20
                text += f"{i}. *{ns['project'][:30]}*\n"
                text += f"   👤 {ns['author']}\n"
                text += f"   📱 {ns['contact']}\n"
                if ns['reason']:
                    text += f"   💬 {ns['reason'][:50]}\n"
                text += "\n"

            if len(no_shows) > 20:
                text += f"... и ещё {len(no_shows) - 20}"

        await query.edit_message_text(
            text,
            reply_markup=back_keyboard(),
            parse_mode="Markdown",
        )


async def problems_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle problem rooms request."""
    query = update.callback_query
    await query.answer()

    if not _is_organizer(query.from_user.id):
        return

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("❌ Нет события.")
            return

        problems = await dashboard_service.get_problem_rooms(session, event.id)

        if not problems:
            text = "✅ *Все залы покрыты*\n\nВо всех залах есть подтверждённые эксперты."
        else:
            text = f"⚠️ *Залы без экспертов ({len(problems)})*\n\n"
            for room in problems:
                text += f"• {room['name']}\n"

            text += "\n💡 Используйте /coverage для детального просмотра."

        await query.edit_message_text(
            text,
            reply_markup=back_keyboard(),
            parse_mode="Markdown",
        )


async def guests_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle guest breakdown request."""
    query = update.callback_query
    await query.answer()

    if not _is_organizer(query.from_user.id):
        return

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("❌ Нет события.")
            return

        stats = await dashboard_service.get_guest_stats(session, event.id)

        if stats.total == 0:
            text = "👥 *Гости*\n\nПока никто не зарегистрировался."
        else:
            # Calculate percentages
            def pct(n):
                return f"{n / stats.total * 100:.0f}%" if stats.total > 0 else "0%"

            text = f"👥 *Гости ({stats.total})*\n\n"

            # Visual breakdown
            text += "📊 *Распределение:*\n"
            text += f"├ 🎓 Студенты: {stats.students} ({pct(stats.students)})\n"
            text += f"├ 📚 Абитуриенты: {stats.applicants} ({pct(stats.applicants)})\n"
            text += f"├ 💼 Бизнес: {stats.business} ({pct(stats.business)})\n"
            text += f"└ 🔹 Другое: {stats.other} ({pct(stats.other)})\n"

            # Bar chart
            total = stats.total
            text += "\n📈 *Диаграмма:*\n"
            for name, count in [
                ("Студенты", stats.students),
                ("Абитуриенты", stats.applicants),
                ("Бизнес", stats.business),
                ("Другое", stats.other),
            ]:
                bar_len = int(count / total * 20) if total > 0 else 0
                bar = "█" * bar_len + "░" * (20 - bar_len)
                text += f"{bar} {name}\n"

        await query.edit_message_text(
            text,
            reply_markup=back_keyboard(),
            parse_mode="Markdown",
        )


async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to dashboard."""
    query = update.callback_query
    await query.answer()

    # Reuse refresh logic
    await refresh_callback(update, context)


def get_dashboard_handlers() -> list:
    """Return list of handlers for EPIC-011."""
    return [
        CommandHandler("dashboard", dashboard_command),
        CallbackQueryHandler(refresh_callback, pattern=r"^dash:refresh$"),
        CallbackQueryHandler(noshows_callback, pattern=r"^dash:noshows$"),
        CallbackQueryHandler(problems_callback, pattern=r"^dash:problems$"),
        CallbackQueryHandler(guests_callback, pattern=r"^dash:guests$"),
        CallbackQueryHandler(back_callback, pattern=r"^dash:back$"),
    ]
