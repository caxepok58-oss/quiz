import logging
from datetime import date, datetime, time, timedelta
from html import escape
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from .db import Database
from .formatting import franchise_color, franchise_name

logger = logging.getLogger(__name__)


def _event_datetime(event_date: str, event_time: str, tz: ZoneInfo) -> datetime:
    hour, minute = (int(x) for x in event_time.split(":"))
    return datetime.combine(date.fromisoformat(event_date), time(hour, minute), tzinfo=tz)


async def _send_reminder(
    bot: Bot, chat_id: int, source: str, title: str, venue: str | None, price: str | None, url: str | None
) -> None:
    price_str = f" · {escape(price)} ₽" if price else ""
    venue_str = escape(venue) if venue else "уточняется"
    title_str = escape(title) if title else "—"
    text = f"⏰ Скоро игра!\n{franchise_color(source)} {franchise_name(source)}{price_str}\n{title_str}\n📍 {venue_str}"
    if url:
        text += f'\n\n<a href="{escape(url)}">Расписание франшизы</a>'
    await bot.send_message(chat_id, text)


async def check_reminders(bot: Bot, db: Database, timezone: str, now: datetime | None = None) -> None:
    """Send a one-time reminder for events starting within each chat's configured lead time."""
    tz = ZoneInfo(timezone)
    now = now or datetime.now(tz)

    candidates = await db.get_reminder_candidates(now.date())
    settings = await db.get_all_reminder_settings()
    if not candidates or not settings:
        return

    events = []
    for source, title, venue, event_date, event_time, price, url, dedup_key in candidates:
        try:
            when = _event_datetime(event_date, event_time, tz)
        except ValueError:
            continue
        events.append((when, source, title, venue, event_date, price, url, dedup_key))

    for chat_id, lead_minutes in settings:
        picked = await db.get_game_reminder_keys(chat_id)
        if not picked:
            continue
        window_end = now + timedelta(minutes=lead_minutes)
        for when, source, title, venue, event_date, price, url, dedup_key in events:
            if dedup_key not in picked:
                continue
            if not (now <= when <= window_end):
                continue
            if await db.was_reminder_sent(chat_id, dedup_key):
                continue
            try:
                await _send_reminder(bot, chat_id, source, title, venue, price, url)
            except TelegramAPIError as exc:
                logger.warning("Failed to send reminder to %s: %s", chat_id, exc)
            await db.mark_reminder_sent(chat_id, dedup_key, event_date)
