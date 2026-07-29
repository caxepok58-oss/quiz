import logging
from datetime import date, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .aggregator import refresh_all
from .db import Database
from .reminders import check_reminders

logger = logging.getLogger(__name__)

_REMINDER_CHECK_MINUTES = 15


def setup_scheduler(db: Database, bot: Bot, scrape_hour: int, timezone: str) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=timezone)

    async def refresh_job() -> None:
        logger.info("Running scheduled quiz-schedule refresh")
        await refresh_all(db)
        await db.purge_old_events(date.today() - timedelta(days=1))

    async def reminder_job() -> None:
        await check_reminders(bot, db, timezone)

    scheduler.add_job(refresh_job, CronTrigger(hour=scrape_hour, minute=0))
    scheduler.add_job(reminder_job, IntervalTrigger(minutes=_REMINDER_CHECK_MINUTES))
    scheduler.start()
    return scheduler
