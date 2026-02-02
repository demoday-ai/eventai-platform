import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.events import router as events_router
from app.api.experts import router as experts_router
from app.api.guests import router as guests_router
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
        from app.services import expert_service, seed_service, user_service

        async with async_session() as session:
            event = await user_service.get_current_event(session)
            if event:
                loaded = await seed_service.load_seed_projects(session, event.id)
                if loaded:
                    logger.info("Seed data loaded: %d projects", loaded)

                expert_loaded = await expert_service.load_seed_experts(session, event.id)
                if expert_loaded:
                    logger.info("Expert seed loaded: %d experts", expert_loaded)
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

    # Setup APScheduler for reminders/escalations
    scheduler = None
    if settings.bot_token and hasattr(app.state, "bot_app"):
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            from app.database import async_session as session_factory
            from app.services import invite_service, user_service as us

            scheduler = AsyncIOScheduler()
            bot_instance = app.state.bot_app.bot

            async def _reminder_job():
                try:
                    async with session_factory() as session:
                        event = await us.get_current_event(session)
                        if event:
                            sent = await invite_service.check_and_send_reminders(
                                session, event.id, bot_instance,
                            )
                            if sent:
                                logger.info("Reminders sent: %d", sent)
                except Exception:
                    logger.exception("Reminder job failed")

            async def _escalation_job():
                try:
                    async with session_factory() as session:
                        event = await us.get_current_event(session)
                        if event:
                            created = await invite_service.check_and_escalate(
                                session, event.id, bot_instance,
                            )
                            if created:
                                logger.info("Escalations created: %d", created)
                except Exception:
                    logger.exception("Escalation job failed")

            scheduler.add_job(_reminder_job, IntervalTrigger(hours=12), id="reminders")
            scheduler.add_job(_escalation_job, IntervalTrigger(hours=12), id="escalations")
            scheduler.start()
            app.state.scheduler = scheduler
            logger.info("APScheduler started (reminders + escalations every 12h)")
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


app = FastAPI(
    title="DemoDay AI Navigator",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(experts_router, prefix="/api/v1")
app.include_router(guests_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
