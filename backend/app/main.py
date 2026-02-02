import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.events import router as events_router
from app.api.projects import router as projects_router
from app.api.users import router as users_router
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DemoDay AI Navigator")

    # Load seed data on startup
    try:
        from app.database import async_session
        from app.services import seed_service, user_service

        async with async_session() as session:
            event = await user_service.get_current_event(session)
            if event:
                loaded = await seed_service.load_seed_projects(session, event.id)
                if loaded:
                    logger.info("Seed data loaded: %d projects", loaded)
    except Exception:
        logger.exception("Failed to load seed data (non-fatal)")

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

    yield

    if hasattr(app.state, "bot_app"):
        bot_app = app.state.bot_app
        if settings.bot_mode == "polling" and bot_app.updater.running:
            await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
        logger.info("Bot stopped")


app = FastAPI(
    title="DemoDay AI Navigator",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
