import asyncio
import logging

import aiohttp

from .db import Database
from .sources import ALL_SOURCES

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PenzaQuizBot/1.0; +https://t.me/)"}


async def refresh_all(db: Database) -> None:
    async with aiohttp.ClientSession(headers=_HEADERS) as session:
        await asyncio.gather(
            *(_refresh_one(db, session, source) for source in ALL_SOURCES),
            return_exceptions=True,
        )


async def _refresh_one(db: Database, session: aiohttp.ClientSession, source) -> None:
    try:
        events = await source.fetch(session)
    except Exception as exc:  # noqa: BLE001 - one source failing must not affect the others
        logger.warning("Source %s failed: %s", source.name, exc)
        await db.set_source_status(source.name, False, str(exc)[:300], 0)
        return
    await db.replace_source_events(source.name, events)
    await db.set_source_status(source.name, True, "ok", len(events))
    logger.info("Source %s: %d events", source.name, len(events))
