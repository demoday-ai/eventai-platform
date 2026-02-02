"""Bot handlers for schedule management and reminders."""

import logging
from datetime import datetime, timedelta
from enum import Enum, auto
from uuid import UUID

import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from app.config import settings
from app.database import async_session
from app.services import notification_service, schedule_service, user_service

logger = logging.getLogger(__name__)
MSK = pytz.timezone("Europe/Moscow")


class ScheduleState(Enum):
    MENU = auto()
    GENERATE = auto()
    REVIEW_ROOM = auto()
    ADJUST_SLOT = auto()
    ADJUST_TIME = auto()
    ADJUST_ROOM = auto()
    APPROVE = auto()
    DASHBOARD = auto()


def _is_organizer(user_id: int) -> bool:
    """Check if Telegram user is an organizer."""
    return user_id in settings.organizer_telegram_ids


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /schedule command - show schedule menu."""
    user = update.effective_user
    if not user or not _is_organizer(user.id):
        await update.message.reply_text("⛔ Эта команда доступна только организаторам.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("📅 Сгенерировать расписание", callback_data="sched:generate")],
        [InlineKeyboardButton("👁 Просмотреть расписание", callback_data="sched:view")],
        [InlineKeyboardButton("✅ Утвердить расписание", callback_data="sched:approve")],
        [InlineKeyboardButton("📋 Превью напоминаний", callback_data="sched:preview")],
        [InlineKeyboardButton("📊 Дашборд доставки", callback_data="sched:dashboard")],
    ]

    await update.message.reply_text(
        "📅 *Управление расписанием*\n\nВыберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return ScheduleState.MENU.value


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle menu button callbacks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user = update.effective_user

    if not user or not _is_organizer(user.id):
        await query.edit_message_text("⛔ Доступ запрещён.")
        return ConversationHandler.END

    if data == "sched:generate":
        return await _handle_generate(query, context)
    elif data == "sched:view":
        return await _handle_view(query, context)
    elif data == "sched:approve":
        return await _handle_approve(query, context)
    elif data == "sched:preview":
        return await _handle_preview(query, context)
    elif data == "sched:dashboard":
        return await _handle_dashboard(query, context)
    elif data == "sched:back":
        return await _show_menu(query)

    return ScheduleState.MENU.value


async def _show_menu(query) -> int:
    """Show main menu."""
    keyboard = [
        [InlineKeyboardButton("📅 Сгенерировать расписание", callback_data="sched:generate")],
        [InlineKeyboardButton("👁 Просмотреть расписание", callback_data="sched:view")],
        [InlineKeyboardButton("✅ Утвердить расписание", callback_data="sched:approve")],
        [InlineKeyboardButton("📋 Превью напоминаний", callback_data="sched:preview")],
        [InlineKeyboardButton("📊 Дашборд доставки", callback_data="sched:dashboard")],
    ]

    await query.edit_message_text(
        "📅 *Управление расписанием*\n\nВыберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return ScheduleState.MENU.value


async def _handle_generate(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generate schedule from approved clustering."""
    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("❌ Нет активного мероприятия.")
            return ConversationHandler.END

        try:
            result = await schedule_service.generate_schedule(session, event.id)
            rooms_text = "\n".join(
                f"• {r.room_name}: {r.slot_count} слотов"
                for r in result.rooms
            )
            await query.edit_message_text(
                f"✅ *Расписание сгенерировано*\n\n"
                f"Всего слотов: {result.total_slots}\n\n"
                f"По залам:\n{rooms_text}\n\n"
                f"Используйте /schedule для утверждения.",
                parse_mode="Markdown",
            )
        except ValueError as e:
            if "already exists" in str(e):
                await query.edit_message_text(
                    "⚠️ Расписание уже существует.\n"
                    "Используйте «Просмотреть расписание» для редактирования."
                )
            else:
                await query.edit_message_text(f"❌ Ошибка: {e}")

    return ConversationHandler.END


async def _handle_view(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """View schedule grouped by rooms."""
    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("❌ Нет активного мероприятия.")
            return ConversationHandler.END

        schedule = await schedule_service.get_schedule(session, event.id)

        if not schedule.days:
            await query.edit_message_text(
                "📅 Расписание пусто.\n"
                "Сначала сгенерируйте расписание.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("« Назад", callback_data="sched:back")]
                ]),
            )
            return ScheduleState.MENU.value

        # Build room buttons
        keyboard = []
        for day in schedule.days:
            keyboard.append([InlineKeyboardButton(
                f"📆 {day.date.strftime('%d.%m.%Y')}",
                callback_data=f"sched:day:{day.date}"
            )])
            for room in day.rooms:
                slot_count = len(room.slots)
                keyboard.append([InlineKeyboardButton(
                    f"  🚪 {room.room_name} ({slot_count} слотов)",
                    callback_data=f"sched:room:{room.room_id}"
                )])

        keyboard.append([InlineKeyboardButton("« Назад", callback_data="sched:back")])

        await query.edit_message_text(
            f"📅 *Расписание: {schedule.event_name}*\n\n"
            f"Выберите зал для просмотра и редактирования:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return ScheduleState.REVIEW_ROOM.value


async def _handle_approve(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Approve the schedule."""
    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("❌ Нет активного мероприятия.")
            return ConversationHandler.END

        try:
            result = await schedule_service.approve_schedule(session, event.id)
            await query.edit_message_text(
                f"✅ *Расписание утверждено*\n\n"
                f"• Слотов: {result['total_slots']}\n"
                f"• Залов: {result['rooms']}\n"
                f"• Дней: {result['days']}\n\n"
                f"Напоминания будут отправлены автоматически.",
                parse_mode="Markdown",
            )
        except ValueError as e:
            await query.edit_message_text(f"❌ Ошибка: {e}")

    return ConversationHandler.END


async def _handle_preview(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Preview eve-of-DD reminders."""
    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("❌ Нет активного мероприятия.")
            return ConversationHandler.END

        if not await schedule_service.is_schedule_approved(session, event.id):
            await query.edit_message_text(
                "⚠️ Расписание не утверждено.\n"
                "Сначала утвердите расписание."
            )
            return ConversationHandler.END

        target_day = event.start_date
        preview = await notification_service.preview_reminders(session, event.id, target_day)

        cancel_btn = "❌ Отменить рассылку" if preview.can_cancel else "⏰ Отмена недоступна"

        keyboard = []
        if preview.can_cancel:
            keyboard.append([InlineKeyboardButton(cancel_btn, callback_data=f"sched_preview_cancel:{target_day}")])
        keyboard.append([InlineKeyboardButton("✅ Подтвердить", callback_data=f"sched_preview_confirm:{target_day}")])
        keyboard.append([InlineKeyboardButton("« Назад", callback_data="sched:back")])

        unreachable_text = ""
        if preview.unreachable:
            unreachable_text = f"\n\n⚠️ Недоступны: {len(preview.unreachable)} участников"

        await query.edit_message_text(
            f"📋 *Превью напоминаний на {target_day}*\n\n"
            f"Отправка: {preview.scheduled_send_time.strftime('%d.%m %H:%M')} MSK\n\n"
            f"*Получатели:*\n"
            f"• 👨‍🎓 Студенты: {preview.recipients.students}\n"
            f"• 👨‍🏫 Эксперты: {preview.recipients.experts}\n"
            f"• 👤 Гости: {preview.recipients.guests}\n"
            f"• 💼 Бизнес: {preview.recipients.business}\n"
            f"• Всего: {preview.recipients.total}"
            f"{unreachable_text}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return ScheduleState.MENU.value


async def _handle_dashboard(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show notification delivery dashboard (T035)."""
    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("❌ Нет активного мероприятия.")
            return ConversationHandler.END

        dashboard = await notification_service.get_notification_dashboard(session, event.id)

        # Build role stats text
        role_text = ""
        for r in dashboard.by_role:
            role_icon = {
                "student": "👨‍🎓",
                "expert": "👨‍🏫",
                "guest": "👤",
                "business": "💼",
            }.get(r.role, "•")
            role_text += f"{role_icon} {r.role}: {r.sent} отпр. / {r.failed} ошибка\n"

        unreachable_text = ""
        if dashboard.unreachable:
            unreachable_text = f"\n⚠️ Недоступны: {len(dashboard.unreachable)} участников"

        keyboard = [
            [InlineKeyboardButton("« Назад", callback_data="sched:back")]
        ]

        await query.edit_message_text(
            f"📊 *Доставка напоминаний*\n\n"
            f"✅ Отправлено: {dashboard.summary.sent}\n"
            f"❌ Ошибка: {dashboard.summary.failed}\n"
            f"⏳ В очереди: {dashboard.summary.pending}\n\n"
            f"*По ролям:*\n{role_text}"
            f"{unreachable_text}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return ScheduleState.DASHBOARD.value


# ========== Room Review Handlers (T029) ==========


async def room_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle room selection to view slots."""
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("sched:room:"):
        return ScheduleState.REVIEW_ROOM.value

    room_id = query.data.split(":")[2]

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            return ConversationHandler.END

        schedule = await schedule_service.get_schedule(
            session, event.id, room_id=UUID(room_id)
        )

        if not schedule.days or not schedule.days[0].rooms:
            await query.edit_message_text("❌ Зал не найден.")
            return ConversationHandler.END

        room = schedule.days[0].rooms[0]

        # Build slot buttons
        keyboard = []
        for slot in room.slots[:20]:  # Limit to 20 slots
            time_str = slot.start_time.astimezone(MSK).strftime("%H:%M")
            status_icon = {"scheduled": "✅", "moved": "🔄", "cancelled": "❌"}.get(slot.status, "")
            title = slot.project_title[:25] + "..." if len(slot.project_title) > 25 else slot.project_title
            keyboard.append([InlineKeyboardButton(
                f"{time_str} {status_icon} {title}",
                callback_data=f"sched:slot:{slot.id}"
            )])

        keyboard.append([InlineKeyboardButton("« Назад к залам", callback_data="sched:view")])

        await query.edit_message_text(
            f"🚪 *{room.room_name}*\n\n"
            f"Слотов: {len(room.slots)}\n"
            f"Нажмите на слот для редактирования:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        context.user_data["current_room_id"] = room_id
        return ScheduleState.REVIEW_ROOM.value


async def slot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle slot selection for adjustment."""
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("sched:slot:"):
        return ScheduleState.REVIEW_ROOM.value

    slot_id = query.data.split(":")[2]
    context.user_data["current_slot_id"] = slot_id

    keyboard = [
        [InlineKeyboardButton("⏰ Перенести время", callback_data=f"sched:adj_time:{slot_id}")],
        [InlineKeyboardButton("🚪 Перенести в другой зал", callback_data=f"sched:adj_room:{slot_id}")],
        [InlineKeyboardButton("❌ Отменить слот", callback_data=f"sched:cancel:{slot_id}")],
        [InlineKeyboardButton("« Назад", callback_data=f"sched:room:{context.user_data.get('current_room_id', '')}")],
    ]

    await query.edit_message_text(
        "🎯 *Редактирование слота*\n\nВыберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return ScheduleState.ADJUST_SLOT.value


async def adjust_slot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle slot adjustment actions."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user = update.effective_user

    if data.startswith("sched:adj_time:"):
        # Show time picker (simplified - just offer 15-min increments)
        slot_id = data.split(":")[2]
        keyboard = []
        now = datetime.now(MSK)

        # Offer times from 10:00 to 19:00 in 15-min increments (simplified to hourly)
        for hour in range(10, 20):
            row = []
            for minute in [0, 30]:
                time_str = f"{hour:02d}:{minute:02d}"
                row.append(InlineKeyboardButton(
                    time_str,
                    callback_data=f"sched:set_time:{slot_id}:{hour}:{minute}"
                ))
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("« Отмена", callback_data=f"sched:slot:{slot_id}")])

        await query.edit_message_text(
            "⏰ Выберите новое время начала:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return ScheduleState.ADJUST_TIME.value

    elif data.startswith("sched:adj_room:"):
        # Show room list
        slot_id = data.split(":")[2]

        async with async_session() as session:
            event = await user_service.get_current_event(session)
            if not event:
                return ConversationHandler.END

            schedule = await schedule_service.get_schedule(session, event.id)

            keyboard = []
            for day in schedule.days:
                for room in day.rooms:
                    keyboard.append([InlineKeyboardButton(
                        f"🚪 {room.room_name}",
                        callback_data=f"sched:set_room:{slot_id}:{room.room_id}"
                    )])
            keyboard.append([InlineKeyboardButton("« Отмена", callback_data=f"sched:slot:{slot_id}")])

            await query.edit_message_text(
                "🚪 Выберите новый зал:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return ScheduleState.ADJUST_ROOM.value

    elif data.startswith("sched:cancel:"):
        slot_id = data.split(":")[2]

        async with async_session() as session:
            event = await user_service.get_current_event(session)
            if not event:
                return ConversationHandler.END

            slot, change_log = await schedule_service.update_slot(
                session, UUID(slot_id),
                {"status": "cancelled"},
                changed_by_user_id=None,  # TODO: get user_id
            )

            if change_log:
                queued = await notification_service.queue_timing_shift_notifications(
                    session, change_log, event.id
                )
                await query.edit_message_text(
                    f"❌ Слот отменён.\n\n"
                    f"Уведомления в очереди: {queued}"
                )
            else:
                await query.edit_message_text("❌ Слот отменён.")

        return ConversationHandler.END

    elif data.startswith("sched:set_time:"):
        parts = data.split(":")
        slot_id, hour, minute = parts[2], int(parts[3]), int(parts[4])

        async with async_session() as session:
            event = await user_service.get_current_event(session)
            if not event:
                return ConversationHandler.END

            # Get current slot to determine date
            current_schedule = await schedule_service.get_schedule(session, event.id)
            new_time = None
            for day in current_schedule.days:
                for room in day.rooms:
                    for s in room.slots:
                        if str(s.id) == slot_id:
                            new_time = MSK.localize(datetime.combine(
                                s.start_time.astimezone(MSK).date(),
                                datetime.min.time().replace(hour=hour, minute=minute)
                            ))
                            break

            if not new_time:
                await query.edit_message_text("❌ Слот не найден.")
                return ConversationHandler.END

            slot, change_log = await schedule_service.update_slot(
                session, UUID(slot_id),
                {
                    "start_time": new_time,
                    "end_time": new_time + timedelta(minutes=15),
                },
            )

            if change_log:
                queued = await notification_service.queue_timing_shift_notifications(
                    session, change_log, event.id
                )
                await query.edit_message_text(
                    f"✅ Время изменено на {hour:02d}:{minute:02d}.\n\n"
                    f"Уведомления в очереди: {queued}"
                )
            else:
                await query.edit_message_text(f"✅ Время изменено на {hour:02d}:{minute:02d}.")

        return ConversationHandler.END

    elif data.startswith("sched:set_room:"):
        parts = data.split(":")
        slot_id, new_room_id = parts[2], parts[3]

        async with async_session() as session:
            event = await user_service.get_current_event(session)
            if not event:
                return ConversationHandler.END

            slot, change_log = await schedule_service.update_slot(
                session, UUID(slot_id),
                {"room_id": UUID(new_room_id)},
            )

            if change_log:
                queued = await notification_service.queue_timing_shift_notifications(
                    session, change_log, event.id
                )
                await query.edit_message_text(
                    f"✅ Зал изменён.\n\n"
                    f"Уведомления в очереди: {queued}"
                )
            else:
                await query.edit_message_text("✅ Зал изменён.")

        return ConversationHandler.END

    return ScheduleState.ADJUST_SLOT.value


# ========== Preview Confirm/Cancel Callbacks (T020) ==========


async def schedule_preview_confirm_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle preview confirm button."""
    query = update.callback_query
    await query.answer("✅ Рассылка подтверждена. Отправка в 18:00 MSK.")

    await query.edit_message_text(
        "✅ Рассылка подтверждена.\n\n"
        "Напоминания будут отправлены автоматически в 18:00 MSK."
    )


async def schedule_preview_cancel_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle preview cancel button."""
    query = update.callback_query
    await query.answer()

    # Extract day from callback data
    day_str = query.data.split(":")[1]

    async with async_session() as session:
        event = await user_service.get_current_event(session)
        if not event:
            await query.edit_message_text("❌ Ошибка: мероприятие не найдено.")
            return

        try:
            from datetime import date as date_type
            target_day = date_type.fromisoformat(day_str)
            cancelled = await notification_service.cancel_reminders(
                session, event.id, target_day
            )
            await query.edit_message_text(
                f"❌ Рассылка отменена.\n\n"
                f"Отменено уведомлений: {cancelled}"
            )
        except notification_service.CancellationWindowClosedError as e:
            await query.edit_message_text(f"⚠️ {e}")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {e}")


# ========== Handler Registration ==========


def get_schedule_handler() -> ConversationHandler:
    """Create and return the schedule conversation handler."""
    return ConversationHandler(
        entry_points=[CommandHandler("schedule", schedule_command)],
        states={
            ScheduleState.MENU.value: [
                CallbackQueryHandler(menu_callback, pattern=r"^sched:"),
            ],
            ScheduleState.REVIEW_ROOM.value: [
                CallbackQueryHandler(room_callback, pattern=r"^sched:room:"),
                CallbackQueryHandler(slot_callback, pattern=r"^sched:slot:"),
                CallbackQueryHandler(menu_callback, pattern=r"^sched:"),
            ],
            ScheduleState.ADJUST_SLOT.value: [
                CallbackQueryHandler(adjust_slot_callback, pattern=r"^sched:"),
            ],
            ScheduleState.ADJUST_TIME.value: [
                CallbackQueryHandler(adjust_slot_callback, pattern=r"^sched:set_time:"),
                CallbackQueryHandler(slot_callback, pattern=r"^sched:slot:"),
            ],
            ScheduleState.ADJUST_ROOM.value: [
                CallbackQueryHandler(adjust_slot_callback, pattern=r"^sched:set_room:"),
                CallbackQueryHandler(slot_callback, pattern=r"^sched:slot:"),
            ],
            ScheduleState.DASHBOARD.value: [
                CallbackQueryHandler(menu_callback, pattern=r"^sched:"),
            ],
        },
        fallbacks=[CommandHandler("schedule", schedule_command)],
        name="schedule_conversation",
        persistent=False,
    )


def get_schedule_preview_handlers() -> list:
    """Return standalone callback handlers for preview confirm/cancel."""
    return [
        CallbackQueryHandler(
            schedule_preview_confirm_callback,
            pattern=r"^sched_preview_confirm:"
        ),
        CallbackQueryHandler(
            schedule_preview_cancel_callback,
            pattern=r"^sched_preview_cancel:"
        ),
    ]
