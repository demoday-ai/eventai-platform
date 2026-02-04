"""Bot handlers for EPIC-006: Organizer Coverage Dashboard.

Standalone /coverage command with inline callback handlers for:
- Coverage summary (room list with status)
- Room drill-down (experts, tags, gaps)
- Gap analysis (uncovered tags + candidate experts)
"""

import logging

from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards import coverage_room_detail_kb, coverage_summary_keyboard
from app.config import settings
from app.database import async_session
from app.models.room import Room
from app.services import coverage_service, user_service

logger = logging.getLogger(__name__)


def _is_organizer(user_id: int) -> bool:
    return str(user_id) in settings.organizer_ids


async def _get_event_id(session):
    event = await user_service.get_current_event(session)
    return event.id if event else None


# ========== /coverage command ==========


async def coverage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /coverage command — show coverage summary for organizers."""
    user_id = update.effective_user.id
    if not _is_organizer(user_id):
        await update.message.reply_text("Эта команда доступна только организаторам.")
        return

    async with async_session() as session:
        event_id = await _get_event_id(session)
        if not event_id:
            await update.message.reply_text("Нет активного мероприятия.")
            return

        await _send_coverage_summary(update.message, session, event_id)


async def coverage_refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cov:refresh callback — refresh coverage summary."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not _is_organizer(user_id):
        await query.edit_message_text("Эта команда доступна только организаторам.")
        return

    async with async_session() as session:
        event_id = await _get_event_id(session)
        if not event_id:
            await query.edit_message_text("Нет активного мероприятия.")
            return

        await _send_coverage_summary(query, session, event_id, edit=True)


async def _send_coverage_summary(target, session, event_id, edit: bool = False):
    """Build and send/edit coverage summary message."""
    dashboard = await coverage_service.get_coverage_summary(session, event_id)
    if not dashboard:
        text = "Нет утверждённого расписания. Сначала запустите кластеризацию."
        if edit:
            await target.edit_message_text(text)
        else:
            await target.reply_text(text)
        return

    rooms = dashboard["rooms"]
    totals = dashboard["totals"]

    indicators = {"covered": "✅", "partial": "⚠️", "uncovered": "❌"}

    lines = ["📊 Покрытие залов\n"]
    for r in rooms:
        ind = indicators.get(r["coverage_level"], "❌")
        pending_str = f"+{r['pending']} ожид." if r["pending"] else ""
        lines.append(
            f"{ind} Зал «{r['room_name']}»: {r['confirmed']} подтв. {pending_str}"
            f" | {r['project_count']} проектов"
        )

    confirmed = totals["confirmed"]
    needed = totals["total_needed"]
    pct = totals["coverage_percent"]
    lines.append(f"\nИтого: {confirmed}/{needed} подтверждено ({pct}%)")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3997] + "..."
    keyboard = coverage_summary_keyboard(rooms)

    if edit:
        await target.edit_message_text(text, reply_markup=keyboard)
    else:
        await target.reply_text(text, reply_markup=keyboard)


# ========== Room drill-down ==========


async def coverage_room_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cov_room:<room_id_prefix> callback — show room detail."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not _is_organizer(user_id):
        await query.edit_message_text("Доступ запрещён.")
        return

    room_id_prefix = query.data.split(":", 1)[1]

    async with async_session() as session:
        event_id = await _get_event_id(session)
        if not event_id:
            await query.edit_message_text("Нет активного мероприятия.")
            return

        # Resolve full room_id from prefix
        room_id = await _resolve_room_id(session, room_id_prefix)
        if not room_id:
            await query.edit_message_text("Зал не найден.")
            return

        await _send_room_detail(query, session, event_id, room_id)


async def coverage_room_refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cov_rr:<room_id_prefix> callback — refresh room detail."""
    query = update.callback_query
    await query.answer()

    room_id_prefix = query.data.split(":", 1)[1]

    async with async_session() as session:
        event_id = await _get_event_id(session)
        if not event_id:
            await query.edit_message_text("Нет активного мероприятия.")
            return

        room_id = await _resolve_room_id(session, room_id_prefix)
        if not room_id:
            await query.edit_message_text("Зал не найден.")
            return

        await _send_room_detail(query, session, event_id, room_id)


async def coverage_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cov:back callback — return to coverage summary."""
    query = update.callback_query
    await query.answer()

    async with async_session() as session:
        event_id = await _get_event_id(session)
        if not event_id:
            await query.edit_message_text("Нет активного мероприятия.")
            return

        await _send_coverage_summary(query, session, event_id, edit=True)


async def _send_room_detail(query, session, event_id, room_id):
    """Build and send room detail message."""
    detail = await coverage_service.get_room_detail(session, event_id, room_id)
    if not detail:
        await query.edit_message_text("Данные по залу не найдены.")
        return

    status_icons = {
        "confirmed": "✅",
        "invited": "📨",
        "invite_ready": "📋",
        "approved": "📋",
        "proposed": "📋",
        "declined": "❌",
        "reassign_requested": "🔄",
        "no_show": "⚠️",
    }

    lines = [f"🔍 Зал «{detail['room_name']}» — {detail['project_count']} проектов\n"]

    # Experts
    if detail["experts"]:
        lines.append("Эксперты:")
        for exp in detail["experts"]:
            icon = status_icons.get(exp["status"], "❓")
            tags_str = ", ".join(exp["tags"][:3]) if exp["tags"] else "—"
            lines.append(f"{icon} {exp['name']} ({exp['status']}) — {tags_str}")
    else:
        lines.append("Эксперты: нет назначенных")

    # Project tags
    if detail["project_tags"]:
        tag_list = ", ".join(detail["project_tags"][:10])
        lines.append(f"\nТематики проектов: {tag_list}")

    # Uncovered tags
    if detail["uncovered_tags"]:
        lines.append(f"\n⚠️ Непокрытые темы: {', '.join(detail['uncovered_tags'][:10])}")

    # Candidates
    if detail["candidates"]:
        lines.append("\nКандидаты:")
        for c in detail["candidates"][:5]:
            rooms_str = f" (сейчас: {', '.join(c['current_rooms'][:2])})" if c["current_rooms"] else " (не назначен)"
            lines.append(f"  • {c['name']}{rooms_str}")

    text = "\n".join(lines)
    # Truncate if exceeding Telegram limit
    if len(text) > 4000:
        text = text[:3997] + "..."

    keyboard = coverage_room_detail_kb(str(room_id))
    await query.edit_message_text(text, reply_markup=keyboard)


# ========== Gap analysis ==========


async def coverage_gaps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cov:gaps callback — show all coverage gaps."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not _is_organizer(user_id):
        await query.edit_message_text("Доступ запрещён.")
        return

    async with async_session() as session:
        event_id = await _get_event_id(session)
        if not event_id:
            await query.edit_message_text("Нет активного мероприятия.")
            return

        gaps_data = await coverage_service.get_coverage_gaps(session, event_id)
        if not gaps_data:
            await query.edit_message_text(
                "Нет утверждённого расписания.",
                reply_markup=coverage_summary_keyboard([]),
            )
            return

        if gaps_data["total_gaps"] == 0:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            await query.edit_message_text(
                "✅ Все тематики покрыты — пробелов нет!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data="cov:back")],
                ]),
            )
            return

        lines = [f"⚠️ Непокрытые тематики ({gaps_data['total_gaps']})\n"]

        current_room = None
        for gap in gaps_data["gaps"]:
            if gap["room_name"] != current_room:
                current_room = gap["room_name"]
                lines.append(f"\nЗал «{current_room}»:")

            lines.append(f"  • {gap['uncovered_tag']} — {gap['project_count_with_tag']} проектов")
            if gap["candidates"]:
                [c["name"] for c in gap["candidates"][:3]]
                rooms_info = []
                for c in gap["candidates"][:3]:
                    r_str = f" ({', '.join(c['current_rooms'][:1])})" if c["current_rooms"] else ""
                    rooms_info.append(f"{c['name']}{r_str}")
                lines.append(f"    Кандидаты: {', '.join(rooms_info)}")
            else:
                lines.append("    Кандидаты: нет подходящих экспертов")

        text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:3997] + "..."

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад", callback_data="cov:back")],
        ])
        await query.edit_message_text(text, reply_markup=keyboard)


# ========== Helpers ==========


async def _resolve_room_id(session, room_id_prefix: str):
    """Find full room UUID from 8-char prefix."""
    result = await session.execute(
        select(Room.id).where(Room.id.cast(type_=None).like(f"{room_id_prefix}%"))
    )
    row = result.first()
    if row:
        return row[0]

    # Fallback: iterate rooms (for UUID cast issues)
    all_rooms = await session.execute(select(Room))
    for room in all_rooms.scalars().all():
        if str(room.id).startswith(room_id_prefix):
            return room.id

    return None
