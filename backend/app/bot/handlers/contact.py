"""Contact Request handlers for EPIC-010.

Callbacks:
  contact:req:{project_id}     — Request contact with project author
  contact:approve:{request_id} — Student approves contact exchange
  contact:reject:{request_id}  — Student rejects contact request
"""

import logging
from uuid import UUID

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
)

from app.database import async_session
from app.models.contact_request import ContactRequestStatus
from app.models.role import RoleCode
from app.services import contact_service, user_service

logger = logging.getLogger(__name__)


def _get_role_display(user) -> str | None:
    """Get role display name for user."""
    if not user.roles:
        return None
    for ur in user.roles:
        if ur.role:
            role_map = {
                RoleCode.GUEST.value: "Гость",
                RoleCode.BUSINESS.value: "Бизнес-партнёр",
                RoleCode.EXPERT.value: "Эксперт",
                RoleCode.ORGANIZER.value: "Организатор",
                RoleCode.STUDENT.value: "Студент",
            }
            return role_map.get(ur.role.code, ur.role.code)
    return None


def contact_request_keyboard(request_id: UUID) -> InlineKeyboardMarkup:
    """Keyboard for student to respond to contact request."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Разрешаю", callback_data=f"contact:approve:{request_id}"),
            InlineKeyboardButton("❌ Не сейчас", callback_data=f"contact:reject:{request_id}"),
        ]
    ])


async def contact_request_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle contact request button click."""
    query = update.callback_query
    await query.answer()

    # Parse project_id
    project_id = query.data.split(":")[-1]

    async with async_session() as session:
        # Get requester user
        requester = await user_service.get_user_by_telegram_id(
            session, str(query.from_user.id)
        )
        if not requester:
            await query.edit_message_text("❌ Пользователь не найден. Начните с /start")
            return

        # Check role (not organizer, not student of this project)
        role_name = _get_role_display(requester)
        if role_name == "Организатор":
            await query.answer("Организаторы не используют эту функцию", show_alert=True)
            return

        # Check for existing request
        existing = await contact_service.get_existing_request(
            session, requester.id, UUID(project_id)
        )
        if existing:
            status_text = {
                ContactRequestStatus.PENDING.value: "⏳ Ваш запрос уже отправлен. Ожидаем ответа автора.",
                ContactRequestStatus.APPROVED.value: "✅ Контакт уже был передан.",
                ContactRequestStatus.REJECTED.value: "❌ Автор отклонил запрос ранее.",
                ContactRequestStatus.EXPIRED.value: "⌛ Запрос истёк. Попробуйте снова.",
            }
            await query.answer(status_text.get(existing.status, "Запрос существует"), show_alert=True)
            return

        # Get student for project
        student = await contact_service.get_student_for_project(session, UUID(project_id))
        if not student:
            await query.answer("❌ Автор проекта не найден в системе", show_alert=True)
            return

        # Check not requesting own project
        if student.id == requester.id:
            await query.answer("Это ваш собственный проект", show_alert=True)
            return

        # Get project info
        from sqlalchemy import select
        from app.models.project import Project
        result = await session.execute(
            select(Project).where(Project.id == UUID(project_id))
        )
        project = result.scalar_one_or_none()
        if not project:
            await query.answer("❌ Проект не найден", show_alert=True)
            return

        # Create request
        request = await contact_service.create_request(
            session, requester.id, UUID(project_id), student.id
        )
        await session.commit()

        # Notify requester
        await query.answer("✅ Запрос отправлен автору")

        # Send notification to student
        if student.telegram_user_id:
            requester_info = contact_service.format_requester_info(requester, role_name)
            try:
                await context.bot.send_message(
                    chat_id=int(student.telegram_user_id),
                    text=(
                        f"📩 *Запрос на контакт*\n\n"
                        f"{requester_info} хочет связаться с вами по проекту "
                        f"*{project.title}*.\n\n"
                        f"Разрешить передачу вашего Telegram-контакта?"
                    ),
                    reply_markup=contact_request_keyboard(request.id),
                    parse_mode="Markdown",
                )
                logger.info("Contact request notification sent to student %s", student.id)
            except Exception as e:
                logger.error("Failed to notify student %s: %s", student.id, e)


async def contact_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle student approval of contact request."""
    query = update.callback_query
    await query.answer()

    request_id = query.data.split(":")[-1]

    async with async_session() as session:
        # Verify sender is the student
        student = await user_service.get_user_by_telegram_id(
            session, str(query.from_user.id)
        )
        if not student:
            await query.edit_message_text("❌ Пользователь не найден")
            return

        request = await contact_service.get_request_by_id(session, UUID(request_id))
        if not request:
            await query.edit_message_text("❌ Запрос не найден")
            return

        if request.student_user_id != student.id:
            await query.answer("Этот запрос не для вас", show_alert=True)
            return

        if request.status != ContactRequestStatus.PENDING.value:
            await query.edit_message_text("ℹ️ Этот запрос уже обработан")
            return

        # Approve
        request = await contact_service.approve_request(session, UUID(request_id))

        # Get contacts
        student_contact = contact_service.get_user_contact(student)
        requester_contact = contact_service.get_user_contact(request.requester)

        # Notify student
        await query.edit_message_text(
            f"✅ *Контакт передан!*\n\n"
            f"Telegram партнёра: {requester_contact or 'не указан'}\n\n"
            f"Вы можете начать общение.",
            parse_mode="Markdown",
        )

        # Notify requester
        if request.requester.telegram_user_id:
            try:
                await context.bot.send_message(
                    chat_id=int(request.requester.telegram_user_id),
                    text=(
                        f"✅ *Автор согласен на контакт!*\n\n"
                        f"Проект: {request.project.title}\n"
                        f"Telegram автора: {student_contact or request.project.telegram_contact}\n\n"
                        f"Теперь можете связаться напрямую."
                    ),
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error("Failed to notify requester: %s", e)


async def contact_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle student rejection of contact request."""
    query = update.callback_query
    await query.answer()

    request_id = query.data.split(":")[-1]

    async with async_session() as session:
        student = await user_service.get_user_by_telegram_id(
            session, str(query.from_user.id)
        )
        if not student:
            await query.edit_message_text("❌ Пользователь не найден")
            return

        request = await contact_service.get_request_by_id(session, UUID(request_id))
        if not request:
            await query.edit_message_text("❌ Запрос не найден")
            return

        if request.student_user_id != student.id:
            await query.answer("Этот запрос не для вас", show_alert=True)
            return

        if request.status != ContactRequestStatus.PENDING.value:
            await query.edit_message_text("ℹ️ Этот запрос уже обработан")
            return

        # Reject
        await contact_service.reject_request(session, UUID(request_id))

        # Notify student
        await query.edit_message_text(
            "❌ Запрос отклонён.\n\n"
            "Партнёр получит уведомление."
        )

        # Notify requester
        if request.requester.telegram_user_id:
            try:
                await context.bot.send_message(
                    chat_id=int(request.requester.telegram_user_id),
                    text=(
                        f"ℹ️ Автор проекта *{request.project.title}* "
                        f"пока не готов к общению.\n\n"
                        f"Попробуйте связаться позже или на Demo Day лично."
                    ),
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error("Failed to notify requester about rejection: %s", e)


def contact_button(project_id: UUID) -> InlineKeyboardButton:
    """Create contact request button for embedding in project cards."""
    return InlineKeyboardButton(
        "📞 Связаться с автором",
        callback_data=f"contact:req:{project_id}"
    )


def get_contact_handlers() -> list:
    """Return list of handlers for EPIC-010."""
    return [
        CallbackQueryHandler(contact_request_callback, pattern=r"^contact:req:"),
        CallbackQueryHandler(contact_approve_callback, pattern=r"^contact:approve:"),
        CallbackQueryHandler(contact_reject_callback, pattern=r"^contact:reject:"),
    ]
