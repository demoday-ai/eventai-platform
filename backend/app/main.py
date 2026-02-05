import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.events import router as events_router
from app.api.experts import router as experts_router
from app.api.guests import router as guests_router
from app.api.leads import router as leads_router
from app.api.participation import router as participation_router
from app.api.projects import router as projects_router
from app.api.reminders import router as reminders_router
from app.api.schedule import router as schedule_router
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

    # Create tables if they don't exist
    try:
        from app.database import engine
        from app.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ensured")
    except Exception:
        logger.exception("Failed to create tables (non-fatal)")

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

                from app.services import organizer_service
                org_seeded = await organizer_service.seed_from_env(session)
                if org_seeded:
                    logger.info("Organizer seed loaded: %d organizers", org_seeded)
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
            from datetime import datetime, timedelta

            import pytz
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger
            from apscheduler.triggers.interval import IntervalTrigger

            from app.database import async_session as session_factory
            from app.services import invite_service, notification_service
            from app.services import user_service as us

            scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Moscow"))
            bot_instance = app.state.bot_app.bot
            MSK = pytz.timezone("Europe/Moscow")

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

            # EPIC-003: Participation acknowledgment periodic jobs
            async def _participation_reminder_job():
                try:
                    from app.services import participation_service
                    async with session_factory() as session:
                        event = await us.get_current_event(session)
                        if event:
                            sent = await participation_service.send_reminders(
                                session, event, bot_instance,
                            )
                            if sent:
                                logger.info("Participation reminders sent: %d", sent)
                except Exception:
                    logger.exception("Participation reminder job failed")

            async def _participation_escalation_job():
                try:
                    from app.services import participation_service
                    async with session_factory() as session:
                        event = await us.get_current_event(session)
                        if event:
                            count = await participation_service.escalate_to_organizers(
                                session, event, bot_instance, settings.organizer_ids,
                            )
                            if count:
                                logger.info("Participation escalations: %d", count)
                except Exception:
                    logger.exception("Participation escalation job failed")

            async def _daily_summary_job():
                try:
                    from app.services import participation_service
                    async with session_factory() as session:
                        event = await us.get_current_event(session)
                        if event:
                            await participation_service.send_daily_summary(
                                session, event, bot_instance, settings.organizer_ids,
                            )
                            logger.info("Daily participation summary sent")
                except Exception:
                    logger.exception("Daily summary job failed")

            # EPIC-005: Eve-of-DD reminder jobs
            async def _eve_reminder_preview_job():
                """Send preview to organizers at 17:00 MSK day before DD."""
                try:
                    async with session_factory() as session:
                        event = await us.get_current_event(session)
                        if not event:
                            return

                        # Check if tomorrow is an event day
                        now = datetime.now(MSK)
                        tomorrow = (now + timedelta(days=1)).date()
                        if event.start_date and tomorrow >= event.start_date:
                            if event.end_date is None or tomorrow <= event.end_date:
                                preview = await notification_service.preview_reminders(
                                    session, event.id, tomorrow
                                )
                                # Send to organizers via bot
                                for org_id in settings.organizer_ids:
                                    try:
                                        msg = (
                                            f"📋 Превью напоминаний на {tomorrow}\n\n"
                                            f"Получателей: {preview.recipients.total}\n"
                                            f"- Студенты: {preview.recipients.students}\n"
                                            f"- Эксперты: {preview.recipients.experts}\n"
                                            f"- Гости: {preview.recipients.guests}\n"
                                            f"- Бизнес: {preview.recipients.business}\n\n"
                                            f"Отправка в 18:00 MSK"
                                        )
                                        await bot_instance.send_message(chat_id=org_id, text=msg)
                                    except Exception:
                                        logger.exception("Failed to send preview to organizer %s", org_id)
                except Exception:
                    logger.exception("Eve reminder preview job failed")

            async def _eve_reminder_send_job():
                """Send eve-of-DD reminders at 18:00 MSK day before DD."""
                try:
                    async with session_factory() as session:
                        event = await us.get_current_event(session)
                        if not event:
                            return

                        now = datetime.now(MSK)
                        tomorrow = (now + timedelta(days=1)).date()
                        if event.start_date and tomorrow >= event.start_date:
                            if event.end_date is None or tomorrow <= event.end_date:
                                from app.services import schedule_service
                                if await schedule_service.is_schedule_approved(session, event.id):
                                    result = await notification_service.send_eve_reminders(
                                        session, event.id, tomorrow, bot_instance
                                    )
                                    logger.info(
                                        "Eve-of-DD reminders sent: %d sent, %d failed, %d skipped",
                                        result.sent, result.failed, result.skipped
                                    )
                except Exception:
                    logger.exception("Eve reminder send job failed")

            # Pre-slot reminder job (every 5 min on DD day)
            async def _pre_slot_reminder_job():
                """Check for slots starting in ~1 hour and send pre-slot reminders."""
                try:
                    async with session_factory() as session:
                        event = await us.get_current_event(session)
                        if not event:
                            return

                        now = datetime.now(MSK)
                        today = now.date()

                        # Check if today is an event day
                        if event.start_date and today >= event.start_date:
                            if event.end_date is None or today <= event.end_date:
                                sent, failed = await notification_service.check_and_send_pre_slot_reminders(
                                    session, event.id, bot_instance
                                )
                                if sent or failed:
                                    logger.info("Pre-slot reminders: %d sent, %d failed", sent, failed)
                except Exception:
                    logger.exception("Pre-slot reminder job failed")

            # Notification batch processor (every 60 sec)
            async def _batch_processor_job():
                """Process pending timing shift notification batches."""
                try:
                    async with session_factory() as session:
                        sent, failed = await notification_service.process_pending_batches(
                            session, bot_instance
                        )
                        if sent or failed:
                            logger.info("Batch processor: %d sent, %d failed", sent, failed)
                except Exception:
                    logger.exception("Batch processor job failed")

            # EPIC-008: Expert briefing job (24h before DD)
            async def _expert_briefing_job():
                """Send expert briefings at 18:00 MSK day before DD."""
                try:
                    from app.services import briefing_service
                    async with session_factory() as session:
                        event = await us.get_current_event(session)
                        if not event:
                            return

                        now = datetime.now(MSK)
                        tomorrow = (now + timedelta(days=1)).date()

                        # Check if tomorrow is the first day of the event
                        if event.start_date and tomorrow == event.start_date:
                            result = await briefing_service.send_all_briefings(
                                session, event.id, bot_instance
                            )
                            logger.info(
                                "Expert briefings sent: %d sent, %d failed, %d skipped",
                                result["sent"], result["failed"], result["skipped"]
                            )
                except Exception:
                    logger.exception("Expert briefing job failed")

            # Register all jobs
            scheduler.add_job(_reminder_job, IntervalTrigger(hours=12), id="expert_reminders")
            scheduler.add_job(_escalation_job, IntervalTrigger(hours=12), id="escalations")

            # EPIC-003 jobs
            scheduler.add_job(
                _participation_reminder_job, IntervalTrigger(hours=1),
                id="participation_reminders",
            )
            scheduler.add_job(
                _participation_escalation_job, IntervalTrigger(hours=1),
                id="participation_escalations",
            )
            scheduler.add_job(
                _daily_summary_job, IntervalTrigger(hours=24),
                id="participation_daily_summary",
            )

            # Eve-of-DD: preview at 17:00, send at 18:00 Moscow time
            scheduler.add_job(
                _eve_reminder_preview_job,
                CronTrigger(hour=17, minute=0, timezone=MSK),
                id="eve_reminder_preview"
            )
            scheduler.add_job(
                _eve_reminder_send_job,
                CronTrigger(hour=18, minute=0, timezone=MSK),
                id="eve_reminder_send"
            )

            # Pre-slot: every 5 minutes
            scheduler.add_job(
                _pre_slot_reminder_job,
                IntervalTrigger(minutes=5),
                id="pre_slot_reminders"
            )

            # Batch processor: every 60 seconds
            scheduler.add_job(
                _batch_processor_job,
                IntervalTrigger(seconds=60),
                id="batch_processor"
            )

            # EPIC-008: Expert briefing at 18:00 MSK day before DD
            scheduler.add_job(
                _expert_briefing_job,
                CronTrigger(hour=18, minute=0, timezone=MSK),
                id="expert_briefing"
            )

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


app = FastAPI(
    title="DemoDay AI Navigator",
    version="0.1.0",
    lifespan=lifespan,
)

from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://team12.camp.aitalenthub.ru",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(experts_router, prefix="/api/v1")
app.include_router(schedule_router, prefix="/api/v1")
app.include_router(guests_router, prefix="/api/v1")
app.include_router(participation_router, prefix="/api/v1")
app.include_router(reminders_router, prefix="/api/v1")
app.include_router(leads_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
