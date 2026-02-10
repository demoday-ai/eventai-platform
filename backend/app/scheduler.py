import logging
from datetime import datetime, timedelta

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

MSK = pytz.timezone("Europe/Moscow")


async def _reminder_job(bot, session_factory):
    try:
        from app.services.admin import invite_service
        from app.services.core import user_service as us

        async with session_factory() as session:
            event = await us.get_current_event(session)
            if event:
                sent = await invite_service.check_and_send_reminders(
                    session, event.id, bot,
                )
                if sent:
                    logger.info("Reminders sent: %d", sent)
    except Exception:
        logger.exception("Reminder job failed")


async def _escalation_job(bot, session_factory):
    try:
        from app.services.admin import invite_service
        from app.services.core import user_service as us

        async with session_factory() as session:
            event = await us.get_current_event(session)
            if event:
                created = await invite_service.check_and_escalate(
                    session, event.id, bot,
                )
                if created:
                    logger.info("Escalations created: %d", created)
    except Exception:
        logger.exception("Escalation job failed")


async def _participation_reminder_job(bot, session_factory):
    try:
        from app.services.admin import participation_service
        from app.services.core import user_service as us

        async with session_factory() as session:
            event = await us.get_current_event(session)
            if event:
                sent = await participation_service.send_reminders(
                    session, event, bot,
                )
                if sent:
                    logger.info("Participation reminders sent: %d", sent)
    except Exception:
        logger.exception("Participation reminder job failed")


async def _participation_escalation_job(bot, session_factory):
    try:
        from app.services.admin import participation_service
        from app.services.core import user_service as us

        async with session_factory() as session:
            event = await us.get_current_event(session)
            if event:
                count = await participation_service.escalate_to_organizers(
                    session, event, bot, settings.organizer_ids,
                )
                if count:
                    logger.info("Participation escalations: %d", count)
    except Exception:
        logger.exception("Participation escalation job failed")



async def _eve_reminder_preview_job(bot, session_factory):
    """Send preview to organizers at 17:00 MSK day before DD."""
    try:
        from app.services.admin import notification_service
        from app.services.core import user_service as us

        async with session_factory() as session:
            event = await us.get_current_event(session)
            if not event:
                return

            now = datetime.now(MSK)
            tomorrow = (now + timedelta(days=1)).date()
            if event.start_date and tomorrow >= event.start_date:
                if event.end_date is None or tomorrow <= event.end_date:
                    preview = await notification_service.preview_reminders(
                        session, event.id, tomorrow
                    )
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
                            await bot.send_message(chat_id=org_id, text=msg)
                        except Exception:
                            logger.exception("Failed to send preview to organizer %s", org_id)
    except Exception:
        logger.exception("Eve reminder preview job failed")


async def _eve_reminder_send_job(bot, session_factory):
    """Send eve-of-DD reminders at 18:00 MSK day before DD."""
    try:
        from app.services.admin import notification_service, schedule_service
        from app.services.core import user_service as us

        async with session_factory() as session:
            event = await us.get_current_event(session)
            if not event:
                return

            now = datetime.now(MSK)
            tomorrow = (now + timedelta(days=1)).date()
            if event.start_date and tomorrow >= event.start_date:
                if event.end_date is None or tomorrow <= event.end_date:
                    if await schedule_service.is_schedule_approved(session, event.id):
                        result = await notification_service.send_eve_reminders(
                            session, event.id, tomorrow, bot
                        )
                        logger.info(
                            "Eve-of-DD reminders sent: %d sent, %d failed, %d skipped",
                            result.sent, result.failed, result.skipped
                        )
    except Exception:
        logger.exception("Eve reminder send job failed")


async def _pre_slot_reminder_job(bot, session_factory):
    """Check for slots starting in ~1 hour and send pre-slot reminders."""
    try:
        from app.services.admin import notification_service
        from app.services.core import user_service as us

        async with session_factory() as session:
            event = await us.get_current_event(session)
            if not event:
                return

            now = datetime.now(MSK)
            today = now.date()

            if event.start_date and today >= event.start_date:
                if event.end_date is None or today <= event.end_date:
                    sent, failed = await notification_service.check_and_send_pre_slot_reminders(
                        session, event.id, bot
                    )
                    if sent or failed:
                        logger.info("Pre-slot reminders: %d sent, %d failed", sent, failed)
    except Exception:
        logger.exception("Pre-slot reminder job failed")


async def _batch_processor_job(bot, session_factory):
    """Process pending timing shift notification batches."""
    try:
        from app.services.admin import notification_service

        async with session_factory() as session:
            sent, failed = await notification_service.process_pending_batches(
                session, bot
            )
            if sent or failed:
                logger.info("Batch processor: %d sent, %d failed", sent, failed)
    except Exception:
        logger.exception("Batch processor job failed")


async def _expert_briefing_job(bot, session_factory):
    """Send expert briefings at 18:00 MSK day before DD."""
    try:
        from app.services.admin import briefing_service
        from app.services.core import user_service as us

        async with session_factory() as session:
            event = await us.get_current_event(session)
            if not event:
                return

            now = datetime.now(MSK)
            tomorrow = (now + timedelta(days=1)).date()

            if event.start_date and tomorrow == event.start_date:
                result = await briefing_service.send_all_briefings(
                    session, event.id, bot
                )
                logger.info(
                    "Expert briefings sent: %d sent, %d failed, %d skipped",
                    result["sent"], result["failed"], result["skipped"]
                )
    except Exception:
        logger.exception("Expert briefing job failed")


def setup_scheduler(bot, session_factory) -> AsyncIOScheduler:
    """Create and configure APScheduler with all periodic jobs."""
    scheduler = AsyncIOScheduler(timezone=MSK)

    scheduler.add_job(
        _reminder_job, IntervalTrigger(hours=12),
        args=[bot, session_factory], id="expert_reminders",
    )
    scheduler.add_job(
        _escalation_job, IntervalTrigger(hours=12),
        args=[bot, session_factory], id="escalations",
    )
    scheduler.add_job(
        _participation_reminder_job, IntervalTrigger(hours=1),
        args=[bot, session_factory], id="participation_reminders",
    )
    scheduler.add_job(
        _participation_escalation_job, IntervalTrigger(hours=1),
        args=[bot, session_factory], id="participation_escalations",
    )
    scheduler.add_job(
        _eve_reminder_preview_job,
        CronTrigger(hour=17, minute=0, timezone=MSK),
        args=[bot, session_factory], id="eve_reminder_preview",
    )
    scheduler.add_job(
        _eve_reminder_send_job,
        CronTrigger(hour=18, minute=0, timezone=MSK),
        args=[bot, session_factory], id="eve_reminder_send",
    )
    scheduler.add_job(
        _pre_slot_reminder_job, IntervalTrigger(minutes=5),
        args=[bot, session_factory], id="pre_slot_reminders",
    )
    scheduler.add_job(
        _batch_processor_job, IntervalTrigger(seconds=60),
        args=[bot, session_factory], id="batch_processor",
    )
    scheduler.add_job(
        _expert_briefing_job,
        CronTrigger(hour=18, minute=0, timezone=MSK),
        args=[bot, session_factory], id="expert_briefing",
    )

    return scheduler
