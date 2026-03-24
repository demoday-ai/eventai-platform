import logging
from pathlib import Path

from telegram import BotCommand
from telegram.ext import Application, MessageHandler, PicklePersistence, filters

from app.bot.handlers.start import get_onboarding_handler, orphan_text_handler
from app.config import settings

logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand("start", "Начать диалог с ботом"),
    BotCommand("support", "Связь с организаторами"),
    BotCommand("program", "Моя программа"),
    BotCommand("profile", "Изменить профиль интересов"),
    BotCommand("help", "Помощь и подсказки"),
]


def create_bot_app() -> Application:
    # Set up persistence to save conversation state across restarts
    persistence_path = Path("/app/data/bot_persistence.pickle")
    persistence_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        persistence = PicklePersistence(filepath=str(persistence_path))
        logger.info("Bot persistence enabled: %s", persistence_path)
    except Exception as e:
        logger.warning("Failed to enable persistence: %s. Using in-memory state.", e)
        persistence = None

    builder = Application.builder().token(settings.bot_token)
    if persistence:
        builder.persistence(persistence)

    application = builder.build()

    # Register bot commands menu
    async def post_init(app: Application) -> None:
        await app.bot.set_my_commands(BOT_COMMANDS)
        logger.info("Bot commands menu registered: %d commands", len(BOT_COMMANDS))

    application.post_init = post_init

    application.add_handler(get_onboarding_handler())

    # Catch-all: text messages from users not in any ConversationHandler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, orphan_text_handler))

    return application
