from datetime import date, datetime, timedelta

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
    updated_at TEXT NOT NULL,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    last_failure_date TEXT,
    alerted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS favorites (
    chat_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (chat_id, source)
);

CREATE TABLE IF NOT EXISTS reminder_settings (
    chat_id INTEGER PRIMARY KEY,
    lead_minutes INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sent_reminders (
    chat_id INTEGER NOT NULL,
    dedup_key TEXT NOT NULL,
    event_date TEXT NOT NULL,
    PRIMARY KEY (chat_id, dedup_key)
);

CREATE TABLE IF NOT EXISTS game_reminders (
    chat_id INTEGER NOT NULL,
    dedup_key TEXT NOT NULL,
    event_date TEXT NOT NULL,
    PRIMARY KEY (chat_id, dedup_key)
);

CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER PRIMARY KEY,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
);
"""

# How many consecutive failed refreshes (roughly, days - refresh runs once/day) before
# alerting admins that a source is down. Only fires once per outage, not every day after.
ALERT_AFTER_DAYS = 3


class Database:
    def __init__(self, path: str):
        self._path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self._path)
        await self._conn.executescript(_SCHEMA)
        await self._migrate()
        await self._conn.commit()

    async def _migrate(self) -> None:
        """Add columns introduced after this table already existed on a deployed DB."""
        conn = self._conn
        cur = await conn.execute("PRAGMA table_info(source_status)")
        columns = {row[1] for row in await cur.fetchall()}
        if "consecutive_failures" not in columns:
            await conn.execute("ALTER TABLE source_status ADD COLUMN consecutive_failures INTEGER NOT NULL DEFAULT 0")
        if "last_failure_date" not in columns:
            await conn.execute("ALTER TABLE source_status ADD COLUMN last_failure_date TEXT")
        if "alerted" not in columns:
            await conn.execute("ALTER TABLE source_status ADD COLUMN alerted INTEGER NOT NULL DEFAULT 0")

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

    async def set_source_status(
        self, source: str, ok: bool, message: str, events_found: int, today: date | None = None
    ) -> bool:
        """Record a source's refresh outcome. Returns True the moment it crosses
        ALERT_AFTER_DAYS consecutive failed days (once per outage, not repeatedly)."""
        conn = self._conn
        cur = await conn.execute(
            "SELECT consecutive_failures, last_failure_date, alerted FROM source_status WHERE source = ?", (source,)
        )
        row = await cur.fetchone()
        consecutive_failures, last_failure_date, alerted = row if row else (0, None, 0)

        should_alert = False
        today = (today or date.today()).isoformat()
        if ok:
            consecutive_failures, last_failure_date, alerted = 0, None, 0
        else:
            if last_failure_date != today:
                consecutive_failures += 1
                last_failure_date = today
            if consecutive_failures >= ALERT_AFTER_DAYS and not alerted:
                should_alert = True
                alerted = 1

        await conn.execute(
            """INSERT INTO source_status
               (source, ok, message, events_found, updated_at, consecutive_failures, last_failure_date, alerted)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(source) DO UPDATE SET
                 ok=excluded.ok, message=excluded.message, events_found=excluded.events_found,
                 updated_at=excluded.updated_at, consecutive_failures=excluded.consecutive_failures,
                 last_failure_date=excluded.last_failure_date, alerted=excluded.alerted""",
            (
                source,
                int(ok),
                message,
                events_found,
                datetime.utcnow().isoformat(),
                consecutive_failures,
                last_failure_date,
                int(alerted),
            ),
        )
        await conn.commit()
        return should_alert

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
        await conn.execute("DELETE FROM sent_reminders WHERE event_date < ?", (before.isoformat(),))
        await conn.execute("DELETE FROM game_reminders WHERE event_date < ?", (before.isoformat(),))
        await conn.commit()

    async def get_last_successful_update(self) -> str | None:
        conn = self._conn
        cur = await conn.execute("SELECT MAX(updated_at) FROM source_status WHERE ok = 1")
        row = await cur.fetchone()
        return row[0] if row else None

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

    async def get_upcoming(self, start: date, end: date, sources: set[str] | None = None):
        conn = self._conn
        params = [start.isoformat(), end.isoformat()]
        source_filter = ""
        if sources:
            placeholders = ",".join("?" * len(sources))
            source_filter = f" AND source IN ({placeholders})"
            params.extend(sources)
        cur = await conn.execute(
            f"""SELECT source, title, venue, address, event_date, event_time, price, url
               FROM events WHERE event_date BETWEEN ? AND ?{source_filter}
               UNION ALL
               SELECT 'manual', title, venue, address, event_date, event_time, price, NULL
               FROM manual_events WHERE event_date BETWEEN ? AND ?
               ORDER BY event_date, event_time""",
            [*params, start.isoformat(), end.isoformat()],
        )
        return await cur.fetchall()

    async def get_day_games_with_ids(self, day: date, sources: set[str] | None = None):
        """(kind, id, source, title, venue, event_time, price, dedup_key) for one day.

        kind is 'e' (events) or 'm' (manual); dedup_key is stable across daily
        re-scrapes and is what reminder picks are keyed by.
        """
        conn = self._conn
        params = [day.isoformat()]
        source_filter = ""
        if sources:
            placeholders = ",".join("?" * len(sources))
            source_filter = f" AND source IN ({placeholders})"
            params.extend(sources)
        cur = await conn.execute(
            f"""SELECT 'e', id, source, title, venue, event_time, price, dedup_key
               FROM events WHERE event_date = ?{source_filter}
               UNION ALL
               SELECT 'm', id, 'manual', title, venue, event_time, price, 'manual-' || id
               FROM manual_events WHERE event_date = ?
               ORDER BY event_time""",
            [*params, day.isoformat()],
        )
        return await cur.fetchall()

    async def get_favorites(self, chat_id: int) -> set[str]:
        conn = self._conn
        cur = await conn.execute("SELECT source FROM favorites WHERE chat_id = ?", (chat_id,))
        return {row[0] for row in await cur.fetchall()}

    async def set_favorite(self, chat_id: int, source: str, enabled: bool) -> None:
        conn = self._conn
        if enabled:
            await conn.execute("INSERT OR IGNORE INTO favorites (chat_id, source) VALUES (?, ?)", (chat_id, source))
        else:
            await conn.execute("DELETE FROM favorites WHERE chat_id = ? AND source = ?", (chat_id, source))
        await conn.commit()

    async def clear_favorites(self, chat_id: int) -> None:
        conn = self._conn
        await conn.execute("DELETE FROM favorites WHERE chat_id = ?", (chat_id,))
        await conn.commit()

    async def set_reminder(self, chat_id: int, lead_minutes: int) -> None:
        conn = self._conn
        await conn.execute(
            """INSERT INTO reminder_settings (chat_id, lead_minutes) VALUES (?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET lead_minutes = excluded.lead_minutes""",
            (chat_id, lead_minutes),
        )
        await conn.commit()

    async def clear_reminder(self, chat_id: int) -> None:
        conn = self._conn
        await conn.execute("DELETE FROM reminder_settings WHERE chat_id = ?", (chat_id,))
        await conn.commit()

    async def get_reminder_minutes(self, chat_id: int) -> int | None:
        conn = self._conn
        cur = await conn.execute("SELECT lead_minutes FROM reminder_settings WHERE chat_id = ?", (chat_id,))
        row = await cur.fetchone()
        return row[0] if row else None

    async def get_all_reminder_settings(self):
        conn = self._conn
        cur = await conn.execute("SELECT chat_id, lead_minutes FROM reminder_settings")
        return await cur.fetchall()

    async def get_reminder_candidates(self, today: date):
        """Auto-scraped and manual events happening today or tomorrow with a known time."""
        conn = self._conn
        tomorrow = (today + timedelta(days=1)).isoformat()
        cur = await conn.execute(
            """SELECT source, title, venue, event_date, event_time, price, url, dedup_key
               FROM events WHERE event_date IN (?, ?) AND event_time IS NOT NULL
               UNION ALL
               SELECT 'manual', title, venue, event_date, event_time, price, NULL, 'manual-' || id
               FROM manual_events WHERE event_date IN (?, ?) AND event_time IS NOT NULL""",
            (today.isoformat(), tomorrow, today.isoformat(), tomorrow),
        )
        return await cur.fetchall()

    async def was_reminder_sent(self, chat_id: int, dedup_key: str) -> bool:
        conn = self._conn
        cur = await conn.execute(
            "SELECT 1 FROM sent_reminders WHERE chat_id = ? AND dedup_key = ?", (chat_id, dedup_key)
        )
        return await cur.fetchone() is not None

    async def mark_reminder_sent(self, chat_id: int, dedup_key: str, event_date: str) -> None:
        conn = self._conn
        await conn.execute(
            "INSERT OR IGNORE INTO sent_reminders (chat_id, dedup_key, event_date) VALUES (?, ?, ?)",
            (chat_id, dedup_key, event_date),
        )
        await conn.commit()

    async def get_event_ref(self, event_id: int):
        """(dedup_key, event_date, source, title, venue, event_time) for a scraped event, by row id."""
        conn = self._conn
        cur = await conn.execute(
            "SELECT dedup_key, event_date, source, title, venue, event_time FROM events WHERE id = ?", (event_id,)
        )
        return await cur.fetchone()

    async def get_manual_event_ref(self, event_id: int):
        """Same shape as get_event_ref, for a manually added event."""
        conn = self._conn
        cur = await conn.execute(
            "SELECT title, venue, event_date, event_time FROM manual_events WHERE id = ?", (event_id,)
        )
        row = await cur.fetchone()
        if not row:
            return None
        title, venue, event_date, event_time = row
        return f"manual-{event_id}", event_date, "manual", title, venue, event_time

    async def touch_user(self, chat_id: int, now: datetime | None = None) -> None:
        """Record that a chat interacted with the bot. Called on every update."""
        conn = self._conn
        stamp = (now or datetime.utcnow()).isoformat()
        await conn.execute(
            """INSERT INTO users (chat_id, first_seen, last_seen) VALUES (?, ?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET last_seen = excluded.last_seen""",
            (chat_id, stamp, stamp),
        )
        await conn.commit()

    async def get_user_stats(self, now: datetime | None = None) -> dict:
        """User counts for /stats: total, actives per window, newcomers, last activity."""
        conn = self._conn
        now = now or datetime.utcnow()
        day, week, month = (now - timedelta(days=n) for n in (1, 7, 30))
        cur = await conn.execute(
            """SELECT COUNT(*),
                      SUM(last_seen >= ?), SUM(last_seen >= ?), SUM(last_seen >= ?),
                      SUM(first_seen >= ?), SUM(first_seen >= ?),
                      MAX(last_seen)
               FROM users""",
            (day.isoformat(), week.isoformat(), month.isoformat(), day.isoformat(), week.isoformat()),
        )
        total, active_day, active_week, active_month, new_day, new_week, last_seen = await cur.fetchone()
        return {
            "total": total,
            "active_day": active_day or 0,
            "active_week": active_week or 0,
            "active_month": active_month or 0,
            "new_day": new_day or 0,
            "new_week": new_week or 0,
            "last_seen": last_seen,
        }

    async def get_game_reminder_keys(self, chat_id: int) -> set[str]:
        conn = self._conn
        cur = await conn.execute("SELECT dedup_key FROM game_reminders WHERE chat_id = ?", (chat_id,))
        return {row[0] for row in await cur.fetchall()}

    async def toggle_game_reminder(self, chat_id: int, dedup_key: str, event_date: str) -> bool:
        """Add/remove a specific game from a chat's reminder picks. Returns the new state (True = subscribed)."""
        conn = self._conn
        cur = await conn.execute(
            "SELECT 1 FROM game_reminders WHERE chat_id = ? AND dedup_key = ?", (chat_id, dedup_key)
        )
        subscribed = await cur.fetchone() is not None
        if subscribed:
            await conn.execute(
                "DELETE FROM game_reminders WHERE chat_id = ? AND dedup_key = ?", (chat_id, dedup_key)
            )
        else:
            await conn.execute(
                "INSERT OR IGNORE INTO game_reminders (chat_id, dedup_key, event_date) VALUES (?, ?, ?)",
                (chat_id, dedup_key, event_date),
            )
        await conn.commit()
        return not subscribed
