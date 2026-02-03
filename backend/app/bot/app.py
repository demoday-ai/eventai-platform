from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from app.bot.handlers.business_profiling import get_business_profiling_handler
from app.bot.handlers.clustering import get_clustering_handler
from app.bot.handlers.confirmation import get_confirmation_handlers
from app.bot.handlers.contact import get_contact_handlers
from app.bot.handlers.dashboard import get_dashboard_handlers
from app.bot.handlers.feedback import get_feedback_handlers
from app.bot.handlers.coverage import (
    coverage_back_callback,
    coverage_command,
    coverage_gaps_callback,
    coverage_refresh_callback,
    coverage_room_callback,
    coverage_room_refresh_callback,
)
from app.bot.handlers.expert_assignment import (
    expert_invite_callback,
    expert_room_choice_callback,
    get_expert_assignment_handler,
)
from app.bot.handlers.guest_profiling import get_profiling_handler
from app.bot.handlers.briefing import get_briefing_handlers
from app.bot.handlers.qa import get_qa_handlers
from app.bot.handlers.reminder import get_reminder_handlers
from app.bot.handlers.schedule import get_schedule_handler, get_schedule_preview_handlers
from app.bot.handlers.start import get_onboarding_handler
from app.config import settings


def create_bot_app() -> Application:
    builder = Application.builder().token(settings.bot_token)
    application = builder.build()

    application.add_handler(get_onboarding_handler())
    application.add_handler(get_clustering_handler())
    application.add_handler(get_business_profiling_handler())
    application.add_handler(get_expert_assignment_handler())
    application.add_handler(get_schedule_handler())
    application.add_handler(get_profiling_handler())

    # Standalone callbacks for expert invite responses (outside conversation)
    application.add_handler(CallbackQueryHandler(expert_invite_callback, pattern=r"^einv:"))
    application.add_handler(CallbackQueryHandler(expert_room_choice_callback, pattern=r"^eroom:"))

    # Standalone callbacks for schedule preview confirm/cancel
    for handler in get_schedule_preview_handlers():
        application.add_handler(handler)

    # EPIC-003: Student schedule acknowledgment handlers
    for handler in get_confirmation_handlers():
        application.add_handler(handler)

    # EPIC-006: Organizer Coverage Dashboard handlers
    application.add_handler(CommandHandler("coverage", coverage_command))
    application.add_handler(CallbackQueryHandler(coverage_refresh_callback, pattern=r"^cov:refresh$"))
    application.add_handler(CallbackQueryHandler(coverage_back_callback, pattern=r"^cov:back$"))
    application.add_handler(CallbackQueryHandler(coverage_gaps_callback, pattern=r"^cov:gaps$"))
    application.add_handler(CallbackQueryHandler(coverage_room_callback, pattern=r"^cov_room:"))
    application.add_handler(CallbackQueryHandler(coverage_room_refresh_callback, pattern=r"^cov_rr:"))

    # EPIC-007: DD Reminders handlers
    for handler in get_reminder_handlers():
        application.add_handler(handler)

    # EPIC-008: Expert Briefing handlers
    for handler in get_briefing_handlers():
        application.add_handler(handler)

    # EPIC-009: Q&A Helper handlers
    for handler in get_qa_handlers():
        application.add_handler(handler)

    # EPIC-010: Contact Request handlers
    for handler in get_contact_handlers():
        application.add_handler(handler)

    # EPIC-011: Organizer Dashboard handlers
    for handler in get_dashboard_handlers():
        application.add_handler(handler)

    # EPIC-012: Student Feedback handlers
    for handler in get_feedback_handlers():
        application.add_handler(handler)

    return application
