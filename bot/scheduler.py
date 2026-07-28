import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .aggregator import refresh_all
from .db import Database

logger = logging.getLogger(__name__)


def setup_scheduler(db: Database, scrape_hour: int, timezone: str) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=timezone)

    async def job() -> None:
        logger.info("Running scheduled quiz-schedule refresh")
        await refresh_all(db)
        await db.purge_old_events(date.today() - timedelta(days=1))

    scheduler.add_job(job, CronTrigger(hour=scrape_hour, minute=0))
    scheduler.start()
    return scheduler
