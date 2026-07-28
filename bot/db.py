from datetime import date, datetime

import aiosqlite

from .models import Event

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    venue TEXT,
    address TEXT,
    event_date TEXT NOT NULL,
    event_time TEXT,
    price TEXT,
    url TEXT,
    dedup_key TEXT NOT NULL UNIQUE,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS manual_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    venue TEXT,
    address TEXT,
    event_date TEXT NOT NULL,
    event_time TEXT,
    price TEXT,
    added_by INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_status (
    source TEXT PRIMARY KEY,
    ok INTEGER NOT NULL,
    message TEXT,
    events_found INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: str):
        self._path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self._path)
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()

    async def replace_source_events(self, source: str, events: list[Event]) -> None:
        conn = self._conn
        now = datetime.utcnow().isoformat()
        await conn.execute("DELETE FROM events WHERE source = ?", (source,))
        for ev in events:
            await conn.execute(
                """INSERT OR REPLACE INTO events
                   (source, title, venue, address, event_date, event_time, price, url, dedup_key, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ev.source,
                    ev.title,
                    ev.venue,
                    ev.address,
                    ev.event_date.isoformat(),
                    ev.event_time.strftime("%H:%M") if ev.event_time else None,
                    ev.price,
                    ev.url,
                    ev.dedup_key(),
                    now,
                ),
            )
        await conn.commit()

    async def set_source_status(self, source: str, ok: bool, message: str, events_found: int) -> None:
        conn = self._conn
        await conn.execute(
            """INSERT INTO source_status (source, ok, message, events_found, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(source) DO UPDATE SET
                 ok=excluded.ok, message=excluded.message,
                 events_found=excluded.events_found, updated_at=excluded.updated_at""",
            (source, int(ok), message, events_found, datetime.utcnow().isoformat()),
        )
        await conn.commit()

    async def get_source_statuses(self):
        conn = self._conn
        cur = await conn.execute(
            "SELECT source, ok, message, events_found, updated_at FROM source_status ORDER BY source"
        )
        return await cur.fetchall()

    async def purge_old_events(self, before: date) -> None:
        conn = self._conn
        await conn.execute("DELETE FROM events WHERE event_date < ?", (before.isoformat(),))
        await conn.execute("DELETE FROM manual_events WHERE event_date < ?", (before.isoformat(),))
        await conn.commit()

    async def add_manual_event(
        self,
        title: str,
        venue: str | None,
        address: str | None,
        event_date: str,
        event_time: str | None,
        price: str | None,
        added_by: int,
    ) -> None:
        conn = self._conn
        await conn.execute(
            """INSERT INTO manual_events (title, venue, address, event_date, event_time, price, added_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, venue, address, event_date, event_time, price, added_by, datetime.utcnow().isoformat()),
        )
        await conn.commit()

    async def list_manual_events(self):
        conn = self._conn
        cur = await conn.execute(
            """SELECT id, title, venue, address, event_date, event_time, price
               FROM manual_events ORDER BY event_date, event_time"""
        )
        return await cur.fetchall()

    async def delete_manual_event(self, event_id: int) -> bool:
        conn = self._conn
        cur = await conn.execute("DELETE FROM manual_events WHERE id = ?", (event_id,))
        await conn.commit()
        return cur.rowcount > 0

    async def get_upcoming(self, start: date, end: date):
        conn = self._conn
        cur = await conn.execute(
            """SELECT source, title, venue, address, event_date, event_time, price, url
               FROM events WHERE event_date BETWEEN ? AND ?
               UNION ALL
               SELECT 'manual', title, venue, address, event_date, event_time, price, NULL
               FROM manual_events WHERE event_date BETWEEN ? AND ?
               ORDER BY event_date, event_time""",
            (start.isoformat(), end.isoformat(), start.isoformat(), end.isoformat()),
        )
        return await cur.fetchall()
