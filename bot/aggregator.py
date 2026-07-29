import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from .db import ALERT_AFTER_DAYS, Database
from .sources import ALL_SOURCES

logger = logging.getLogger(__name__)


async def refresh_all(db: Database, bot: Bot | None = None, admin_ids: set[int] | None = None) -> None:
    await asyncio.gather(
        *(_refresh_one(db, source, bot, admin_ids) for source in ALL_SOURCES),
        return_exceptions=True,
    )


async def _alert_admins(bot: Bot, admin_ids: set[int], source: str, message: str) -> None:
    text = (
        f"⚠️ Источник «{source}» не отдаёт данные уже {ALERT_AFTER_DAYS}-й день подряд.\n"
        f"Ошибка: {message}\n\nПроверьте /sources."
    )
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except TelegramAPIError as exc:
            logger.warning("Failed to alert admin %s about source %s: %s", admin_id, source, exc)


async def _refresh_one(db: Database, source, bot: Bot | None, admin_ids: set[int] | None) -> None:
    try:
        events = await source.fetch()
    except Exception as exc:  # noqa: BLE001 - one source failing must not affect the others
        logger.warning("Source %s failed: %s", source.name, exc)
        should_alert = await db.set_source_status(source.name, False, str(exc)[:300], 0)
        if should_alert and bot and admin_ids:
            await _alert_admins(bot, admin_ids, source.name, str(exc)[:300])
        return
    await db.replace_source_events(source.name, events)
    await db.set_source_status(source.name, True, "ok", len(events))
    logger.info("Source %s: %d events", source.name, len(events))
