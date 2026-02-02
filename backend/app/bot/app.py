from telegram.ext import Application

from app.bot.handlers.start import get_onboarding_handler
from app.config import settings


def create_bot_app() -> Application:
    builder = Application.builder().token(settings.bot_token)
    application = builder.build()

    application.add_handler(get_onboarding_handler())

    return application
