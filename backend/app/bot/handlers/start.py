import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from app.bot.keyboards import (
    confirm_change_keyboard,
    guest_subtype_keyboard,
    role_keyboard,
    start_profiling_keyboard,
)
from app.config import settings
from app.database import async_session
from app.models.role import ROLE_DISPLAY_NAMES, RoleCode
from app.models.user import GUEST_SUBTYPE_DISPLAY, GuestSubtype
from app.services import user_service

logger = logging.getLogger(__name__)

# Conversation states
CHOOSE_ROLE, CHOOSE_SUBTYPE, CONFIRM_CHANGE = range(3)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Check if this is an expert deep link: /start expert
    if context.args and context.args[0] == "expert":
        from app.bot.handlers.expert_assignment import handle_expert_start
        return await handle_expert_start(update, context)

    tg_user = update.effective_user
    telegram_user_id = str(tg_user.id)
    full_name = tg_user.full_name or tg_user.first_name
    username = tg_user.username

    async with async_session() as session:
        user = await user_service.upsert_user(
            session, telegram_user_id, full_name, username
        )

        event = await user_service.get_current_event(session)
        if not event:
            await update.message.reply_text("Нет активного события. Попробуйте позже.")
            return ConversationHandler.END

        role = await user_service.get_user_role_with_info(session, user.id, event.id)

    is_organizer = telegram_user_id in settings.organizer_ids
    logger.info("start: user=%s tg_id=%s has_role=%s", full_name, telegram_user_id, role is not None)

    if role:
        role_name = ROLE_DISPLAY_NAMES.get(RoleCode(role.code), role.code)
        context.user_data["current_role"] = role.code
        context.user_data["event_id"] = str(event.id)
        await update.message.reply_text(
            f"С возвращением, {full_name}!\n"
            f"Ваша роль: {role_name}\n\n"
            f"Хотите сменить роль?",
            reply_markup=confirm_change_keyboard(),
        )
        return CONFIRM_CHANGE

    context.user_data["event_id"] = str(event.id)
    await update.message.reply_text(
        f"Добро пожаловать на Demo Day, {full_name}!\n\n"
        f"Выберите вашу роль:",
        reply_markup=role_keyboard(is_organizer),
    )
    return CHOOSE_ROLE


async def role_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    _, role_code_str = query.data.split(":", 1)
    role_code = RoleCode(role_code_str)

    if role_code == RoleCode.ORGANIZER:
        telegram_user_id = str(query.from_user.id)
        if telegram_user_id not in settings.organizer_ids:
            await query.edit_message_text("Роль организатора доступна только по приглашению.")
            return ConversationHandler.END

    tg_user = query.from_user
    telegram_user_id = str(tg_user.id)

    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(session, telegram_user_id)
        event = await user_service.get_current_event(session)
        role = await user_service.get_role_by_code(session, role_code)

        if not role or not event or not user:
            await query.edit_message_text("Ошибка. Попробуйте /start заново.")
            return ConversationHandler.END

        if role_code == RoleCode.GUEST:
            context.user_data["pending_role_id"] = str(role.id)
            context.user_data["pending_role_code"] = role_code.value
            await query.edit_message_text(
                "Уточните, кто вы:",
                reply_markup=guest_subtype_keyboard(),
            )
            return CHOOSE_SUBTYPE

        await user_service.set_role(session, user.id, event.id, role)

    role_name = ROLE_DISPLAY_NAMES.get(role_code, role_code_str)
    logger.info("role_chosen: tg_id=%s role=%s", telegram_user_id, role_code.value)
    await query.edit_message_text(f"Отлично! Ваша роль: {role_name}\n\nДобро пожаловать!")

    # Auto-trigger profiling for Business role (EPIC-005)
    if role_code == RoleCode.BUSINESS:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Укажите интересы для персональной программы Demo Day:",
            reply_markup=start_profiling_keyboard(),
        )

    return ConversationHandler.END


async def subtype_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    _, subtype_str = query.data.split(":", 1)
    guest_subtype = GuestSubtype(subtype_str)

    tg_user = query.from_user
    telegram_user_id = str(tg_user.id)

    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(session, telegram_user_id)
        event = await user_service.get_current_event(session)
        role = await user_service.get_role_by_code(session, RoleCode.GUEST)

        if not role or not event or not user:
            await query.edit_message_text("Ошибка. Попробуйте /start заново.")
            return ConversationHandler.END

        await user_service.set_role(
            session, user.id, event.id, role, guest_subtype=guest_subtype
        )

    subtype_name = GUEST_SUBTYPE_DISPLAY.get(guest_subtype, subtype_str)
    logger.info("subtype_chosen: tg_id=%s subtype=%s", telegram_user_id, subtype_str)
    await query.edit_message_text(
        f"Отлично! Ваша роль: Гость ({subtype_name})\n\nДобро пожаловать!"
    )

    # Auto-trigger profiling after guest onboarding (EPIC-005)
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Укажите интересы для персональной программы Demo Day:",
        reply_markup=start_profiling_keyboard(),
    )

    return ConversationHandler.END


async def confirm_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    _, choice = query.data.split(":", 1)

    if choice == "no":
        await query.edit_message_text("Хорошо, роль не изменена.")
        return ConversationHandler.END

    is_organizer = str(query.from_user.id) in settings.organizer_ids
    await query.edit_message_text(
        "Выберите новую роль:",
        reply_markup=role_keyboard(is_organizer),
    )
    return CHOOSE_ROLE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END


def get_onboarding_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            CommandHandler("role", start_command),
        ],
        states={
            CHOOSE_ROLE: [
                CallbackQueryHandler(role_chosen, pattern=r"^role:"),
            ],
            CHOOSE_SUBTYPE: [
                CallbackQueryHandler(subtype_chosen, pattern=r"^subtype:"),
            ],
            CONFIRM_CHANGE: [
                CallbackQueryHandler(confirm_change, pattern=r"^change:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
