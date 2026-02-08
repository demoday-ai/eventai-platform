from telegram.ext import Application, MessageHandler, filters

from app.bot.handlers.start import get_onboarding_handler, orphan_text_handler
from app.config import settings


def create_bot_app() -> Application:
    builder = Application.builder().token(settings.bot_token)
    application = builder.build()

    application.add_handler(get_onboarding_handler())

    # Catch-all: text messages from users not in any ConversationHandler
    # (e.g. after container restart when in-memory state is lost)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, orphan_text_handler)
    )

    return application
