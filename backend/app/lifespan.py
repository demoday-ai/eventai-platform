import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DemoDay AI Navigator")

    # Create tables if they don't exist
    try:
        from app.database import engine
        from app.models import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ensured")
    except Exception:
        logger.exception("Failed to create tables (non-fatal)")

    # Seed organizers from env on startup
    try:
        from app.database import async_session
        from app.services.core import user_service

        async with async_session() as session:
            event = await user_service.get_current_event(session)
            if event:
                from app.services.admin import organizer_service

                org_seeded = await organizer_service.seed_from_env(session)
                if org_seeded:
                    logger.info("Organizer seed loaded: %d organizers", org_seeded)
    except Exception:
        logger.exception("Failed to seed organizers (non-fatal)")

    # Load LLM API keys from DB into KeyManager
    try:
        from sqlalchemy import select

        from app.database import async_session
        from app.models.llm_api_key import LlmApiKey
        from app.services.core.llm_client import get_key_manager

        async with async_session() as session:
            result = await session.execute(select(LlmApiKey).where(LlmApiKey.is_active))
            db_keys = result.scalars().all()

            if db_keys:
                key_manager = get_key_manager()
                # Inject keys from DB
                key_manager._db_keys = [k.api_key for k in db_keys]
                logger.info("Loaded %d LLM API keys from database", len(db_keys))
            else:
                # Seed keys from env to DB if DB is empty
                env_keys = settings.api_keys
                if env_keys:
                    for api_key in env_keys:
                        new_key = LlmApiKey(
                            api_key=api_key,
                            key_suffix=api_key[-8:],
                            is_active=True,
                        )
                        session.add(new_key)
                    await session.commit()
                    logger.info("Seeded %d LLM API keys from env to DB", len(env_keys))

                    # Reload keys into KeyManager
                    key_manager = get_key_manager()
                    key_manager._db_keys = env_keys
                else:
                    logger.info("No LLM API keys in DB or env, using fallback")
    except Exception:
        logger.exception("Failed to load LLM keys from DB (non-fatal, will use env)")

    if settings.bot_token:
        from app.bot.app import create_bot_app

        bot_app = create_bot_app()

        if settings.bot_mode == "webhook":
            webhook_path = "/bot/webhook"
            webhook_full = f"{settings.webhook_url}{webhook_path}"
            await bot_app.initialize()
            await bot_app.bot.set_webhook(webhook_full)
            await bot_app.start()
            logger.info("Bot started in webhook mode: %s", webhook_full)

            from telegram.ext import Application

            async def webhook_handler(request):
                from starlette.responses import Response

                data = await request.json()
                update = Application.de_json(data, bot_app.bot)
                await bot_app.process_update(update)
                return Response(status_code=200)

            app.add_api_route(webhook_path, webhook_handler, methods=["POST"])
        else:
            await bot_app.initialize()
            await bot_app.start()
            await bot_app.updater.start_polling()
            logger.info("Bot started in polling mode")

        app.state.bot_app = bot_app
    else:
        logger.warning("BOT_TOKEN not set — bot disabled")

    # Setup APScheduler for reminders/escalations
    if settings.bot_token and hasattr(app.state, "bot_app"):
        try:
            from app.database import async_session as session_factory
            from app.scheduler import setup_scheduler

            bot_instance = app.state.bot_app.bot
            scheduler = setup_scheduler(bot_instance, session_factory)
            scheduler.start()
            app.state.scheduler = scheduler
            logger.info(
                "APScheduler started: expert reminders (12h), escalations (12h), "
                "participation jobs (1h/24h), eve-of-DD (17:00/18:00 MSK), "
                "pre-slot (5min), batch processor (60s), expert briefing (18:00 MSK)"
            )
        except Exception:
            logger.exception("Failed to start APScheduler (non-fatal)")

    yield

    # Shutdown scheduler
    if hasattr(app.state, "scheduler") and app.state.scheduler:
        app.state.scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")

    if hasattr(app.state, "bot_app"):
        bot_app = app.state.bot_app
        if settings.bot_mode == "polling" and bot_app.updater.running:
            await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
        logger.info("Bot stopped")
