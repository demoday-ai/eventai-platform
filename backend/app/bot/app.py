import logging
from pathlib import Path

from telegram.ext import Application, MessageHandler, PicklePersistence, filters

from app.bot.handlers.start import get_onboarding_handler, orphan_text_handler
from app.config import settings

logger = logging.getLogger(__name__)


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

    application.add_handler(get_onboarding_handler())

    # Catch-all: text messages from users not in any ConversationHandler
    # Still useful as fallback for edge cases
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, orphan_text_handler))

    return application
