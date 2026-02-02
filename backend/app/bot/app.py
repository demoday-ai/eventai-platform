from telegram.ext import Application, CallbackQueryHandler

from app.bot.handlers.clustering import get_clustering_handler
from app.bot.handlers.expert_assignment import (
    expert_invite_callback,
    expert_room_choice_callback,
    get_expert_assignment_handler,
)
from app.bot.handlers.schedule import get_schedule_handler, get_schedule_preview_handlers
from app.bot.handlers.start import get_onboarding_handler
from app.config import settings


def create_bot_app() -> Application:
    builder = Application.builder().token(settings.bot_token)
    application = builder.build()

    application.add_handler(get_onboarding_handler())
    application.add_handler(get_clustering_handler())
    application.add_handler(get_expert_assignment_handler())
    application.add_handler(get_schedule_handler())

    # Standalone callbacks for expert invite responses (outside conversation)
    application.add_handler(CallbackQueryHandler(expert_invite_callback, pattern=r"^einv:"))
    application.add_handler(CallbackQueryHandler(expert_room_choice_callback, pattern=r"^eroom:"))

    # Standalone callbacks for schedule preview confirm/cancel
    for handler in get_schedule_preview_handlers():
        application.add_handler(handler)

    return application
