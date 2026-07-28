import asyncio
import logging

from .db import Database
from .sources import ALL_SOURCES

logger = logging.getLogger(__name__)


async def refresh_all(db: Database) -> None:
    await asyncio.gather(
        *(_refresh_one(db, source) for source in ALL_SOURCES),
        return_exceptions=True,
    )


async def _refresh_one(db: Database, source) -> None:
    try:
        events = await source.fetch()
    except Exception as exc:  # noqa: BLE001 - one source failing must not affect the others
        logger.warning("Source %s failed: %s", source.name, exc)
        await db.set_source_status(source.name, False, str(exc)[:300], 0)
        return
    await db.replace_source_events(source.name, events)
    await db.set_source_status(source.name, True, "ok", len(events))
    logger.info("Source %s: %d events", source.name, len(events))
