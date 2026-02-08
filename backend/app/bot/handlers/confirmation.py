"""Student schedule acknowledgment handlers (EPIC-003).

Commands:
  /broadcast — Organizer broadcasts schedule slots to students
  /status — Organizer views acknowledgment summary

Callbacks:
  ack:{id}     — Student acknowledges slot
  bcast:yes/no — Organizer confirms/cancels broadcast
  proom:{id}   — Organizer drills into room details
  pstat:refresh — Organizer refreshes summary
"""

import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from app.bot.utils import is_organizer
from app.database import async_session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# /broadcast command
# ---------------------------------------------------------------------------


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_organizer(update.effective_user.id):
        await update.message.reply_text("Только для организаторов.")
        return

    from app.bot.keyboards import broadcast_confirm_keyboard
    from app.services import participation_service, user_service

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await update.message.reply_text("Нет текущего события.")
            return

        clustering = await participation_service.get_approved_clustering_run(
            session, event.id
        )
        if not clustering:
            await update.message.reply_text(
                "Нет утверждённого расписания. Сначала запустите кластеризацию."
            )
            return

    await update.message.reply_text(
        "Разослать расписание всем студентам?",
        reply_markup=broadcast_confirm_keyboard(),
    )


async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_organizer(query.from_user.id):
        await query.edit_message_text("Только для организаторов.")
        return

    action = query.data.split(":")[1]

    if action == "no":
        await query.edit_message_text("Рассылка отменена.")
        return

    # action == "yes"
    await query.edit_message_text("⏳ Рассылка запущена...")

    from app.services import participation_service, user_service

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("Нет текущего события.")
            return

        try:
            result = await participation_service.broadcast_slots(
                session, event, context.bot
            )
        except ValueError as e:
            await query.edit_message_text(f"Ошибка: {e}")
            return

    text = (
        f"✅ Рассылка завершена\n\n"
        f"Отправлено: {result['sent']}\n"
        f"Пропущено (не изменились): {result['skipped']}\n"
        f"Ошибки доставки: {result['failed']}\n"
        f"Неподключённые: {result['unregistered']}"
    )

    if result["unregistered_projects"]:
        text += "\n\nНеподключённые студенты:"
        for p in result["unregistered_projects"][:10]:
            text += f"\n• {p['project_title']} ({p['telegram_contact']})"
        if len(result["unregistered_projects"]) > 10:
            text += f"\n... и ещё {len(result['unregistered_projects']) - 10}"

    await query.edit_message_text(text)


# ---------------------------------------------------------------------------
# Student acknowledgment callback
# ---------------------------------------------------------------------------


async def acknowledge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    short_id = query.data.split(":")[1]

    from app.services import participation_service

    async with async_session() as session:
        success, message = await participation_service.acknowledge_participation(
            session, short_id, str(query.from_user.id)
        )

    await query.answer(message, show_alert=not success)
    if success:
        # Edit original message to remove button
        try:
            original_text = query.message.text or ""
            await query.edit_message_text(
                original_text + "\n\n✅ Ознакомлен",
                reply_markup=None,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# /status command
# ---------------------------------------------------------------------------


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_organizer(update.effective_user.id):
        await update.message.reply_text("Только для организаторов.")
        return

    from app.bot.keyboards import participation_summary_rooms
    from app.services import participation_service, user_service

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await update.message.reply_text("Нет текущего события.")
            return

        summary = await participation_service.get_participation_summary(
            session, event.id
        )

    text = (
        f"📊 Сводка ознакомлений\n\n"
        f"Всего: {summary['total']}\n"
        f"Ознакомились: {summary['acknowledged']}\n"
        f"Не ответили: {summary['pending']}\n"
        f"Неподключённые: {summary['unregistered']}\n\n"
        f"Залы:"
    )

    if summary["by_room"]:
        keyboard = participation_summary_rooms(summary["by_room"])
        await update.message.reply_text(text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text + "\nНет данных по залам.")


async def room_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_organizer(query.from_user.id):
        return

    short_room_id = query.data.split(":")[1]

    from app.services import participation_service, user_service

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("Нет текущего события.")
            return

        # Find room by short ID
        from sqlalchemy import select

        from app.models.room import Room

        result = await session.execute(
            select(Room).where(Room.id.cast(str).like(f"{short_room_id}%"))
        )
        room = result.scalar_one_or_none()
        if not room:
            await query.edit_message_text("Зал не найден.")
            return

        items = await participation_service.get_unacknowledged_list(
            session, event.id, room.id
        )

    if not items:
        text = f"✅ Зал «{room.name}»: все ознакомлены!"
    else:
        text = f"⏳ Зал «{room.name}» — не ознакомлены ({len(items)}):\n"
        for item in items[:15]:
            reminder = " 🔔" if item["reminder_sent"] else ""
            text += f"\n• {item['project_title']} ({item['telegram_contact']}){reminder}"
        if len(items) > 15:
            text += f"\n... и ещё {len(items) - 15}"

    from app.bot.keyboards import participation_summary_rooms
    from app.services import participation_service as ps
    from app.services import user_service

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        summary = await ps.get_participation_summary(session, event.id)

    keyboard = participation_summary_rooms(summary["by_room"])
    await query.edit_message_text(text, reply_markup=keyboard)


async def refresh_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Обновляю...")

    if not is_organizer(query.from_user.id):
        return

    from app.bot.keyboards import participation_summary_rooms
    from app.services import participation_service, user_service

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("Нет текущего события.")
            return

        summary = await participation_service.get_participation_summary(
            session, event.id
        )

    text = (
        f"📊 Сводка ознакомлений\n\n"
        f"Всего: {summary['total']}\n"
        f"Ознакомились: {summary['acknowledged']}\n"
        f"Не ответили: {summary['pending']}\n"
        f"Неподключённые: {summary['unregistered']}\n\n"
        f"Залы:"
    )

    keyboard = participation_summary_rooms(summary["by_room"])
    await query.edit_message_text(text, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------


def get_confirmation_handlers() -> list:
    """Return list of handlers for EPIC-003."""
    return [
        CommandHandler("broadcast", broadcast_command),
        CommandHandler("status", status_command),
        CallbackQueryHandler(broadcast_callback, pattern=r"^bcast:"),
        CallbackQueryHandler(acknowledge_callback, pattern=r"^ack:"),
        CallbackQueryHandler(room_detail_callback, pattern=r"^proom:"),
        CallbackQueryHandler(refresh_status_callback, pattern=r"^pstat:"),
    ]
