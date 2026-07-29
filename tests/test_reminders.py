from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio

from bot.db import Database
from bot.models import Event
from bot.reminders import check_reminders

_TZ = ZoneInfo("Europe/Moscow")
_NOW = datetime(2026, 8, 5, 17, 0, tzinfo=_TZ)
_SOON = (_NOW + timedelta(hours=1)).time()


@pytest_asyncio.fixture
async def db():
    database = Database(":memory:")
    await database.connect()
    yield database
    await database.close()


async def _dedup_key(db: Database, day, title: str) -> str:
    """Look up the stable dedup_key the aggregator assigned to a just-inserted event."""
    candidates = await db.get_reminder_candidates(day)
    return next(row[7] for row in candidates if row[1] == title)


@pytest.mark.asyncio
async def test_sends_reminder_only_for_picked_game_and_not_again(db):
    await db.replace_source_events(
        "quizplease", [Event(source="quizplease", title="Игра А", event_date=_NOW.date(), event_time=_SOON)]
    )
    await db.set_reminder(chat_id=1, lead_minutes=180)
    key = await _dedup_key(db, _NOW.date(), "Игра А")
    await db.toggle_game_reminder(1, key, _NOW.date().isoformat())
    bot = AsyncMock()

    await check_reminders(bot, db, "Europe/Moscow", now=_NOW)
    assert bot.send_message.await_count == 1
    args, _ = bot.send_message.call_args
    assert args[0] == 1
    assert "Игра А" in args[1]

    bot.send_message.reset_mock()
    await check_reminders(bot, db, "Europe/Moscow", now=_NOW)
    assert bot.send_message.await_count == 0


@pytest.mark.asyncio
async def test_skips_event_outside_lead_window_even_if_picked(db):
    far = (_NOW + timedelta(hours=10)).time()
    await db.replace_source_events(
        "quizplease", [Event(source="quizplease", title="Игра далеко", event_date=_NOW.date(), event_time=far)]
    )
    await db.set_reminder(chat_id=1, lead_minutes=180)
    key = await _dedup_key(db, _NOW.date(), "Игра далеко")
    await db.toggle_game_reminder(1, key, _NOW.date().isoformat())
    bot = AsyncMock()

    await check_reminders(bot, db, "Europe/Moscow", now=_NOW)
    assert bot.send_message.await_count == 0


@pytest.mark.asyncio
async def test_only_explicitly_picked_games_get_reminded(db):
    await db.replace_source_events(
        "quizplease", [Event(source="quizplease", title="Квиз плиз игра", event_date=_NOW.date(), event_time=_SOON)]
    )
    await db.replace_source_events(
        "shakerquiz", [Event(source="shakerquiz", title="Шейкер игра", event_date=_NOW.date(), event_time=_SOON)]
    )
    await db.add_manual_event("Ручная игра", "Клуб", None, _NOW.date().isoformat(), _SOON.strftime("%H:%M"), None, added_by=1)

    await db.set_reminder(chat_id=1, lead_minutes=180)
    key = await _dedup_key(db, _NOW.date(), "Шейкер игра")
    await db.toggle_game_reminder(1, key, _NOW.date().isoformat())
    bot = AsyncMock()

    await check_reminders(bot, db, "Europe/Moscow", now=_NOW)

    sent_texts = [call.args[1] for call in bot.send_message.await_args_list]
    assert len(sent_texts) == 1
    assert "Шейкер игра" in sent_texts[0]


@pytest.mark.asyncio
async def test_reminders_enabled_but_nothing_picked_means_no_messages(db):
    await db.replace_source_events(
        "quizplease", [Event(source="quizplease", title="Игра А", event_date=_NOW.date(), event_time=_SOON)]
    )
    await db.set_reminder(chat_id=1, lead_minutes=180)
    bot = AsyncMock()

    await check_reminders(bot, db, "Europe/Moscow", now=_NOW)
    assert bot.send_message.await_count == 0


@pytest.mark.asyncio
async def test_no_reminder_settings_means_no_messages_even_if_picked(db):
    await db.replace_source_events(
        "quizplease", [Event(source="quizplease", title="Игра А", event_date=_NOW.date(), event_time=_SOON)]
    )
    key = await _dedup_key(db, _NOW.date(), "Игра А")
    await db.toggle_game_reminder(1, key, _NOW.date().isoformat())
    bot = AsyncMock()

    await check_reminders(bot, db, "Europe/Moscow", now=_NOW)
    assert bot.send_message.await_count == 0
