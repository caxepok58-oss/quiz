from datetime import date, time

import pytest
import pytest_asyncio

from bot.db import Database
from bot.models import Event


@pytest_asyncio.fixture
async def db():
    database = Database(":memory:")
    await database.connect()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_get_upcoming_filters_by_source(db):
    await db.replace_source_events(
        "quizplease",
        [Event(source="quizplease", title="Игра А", event_date=date(2026, 8, 5), event_time=time(19, 0))],
    )
    await db.replace_source_events(
        "shakerquiz",
        [Event(source="shakerquiz", title="Игра Б", event_date=date(2026, 8, 5), event_time=time(20, 0))],
    )

    all_rows = await db.get_upcoming(date(2026, 8, 1), date(2026, 8, 31))
    assert {r[0] for r in all_rows} == {"quizplease", "shakerquiz"}

    filtered = await db.get_upcoming(date(2026, 8, 1), date(2026, 8, 31), {"quizplease"})
    assert [r[0] for r in filtered] == ["quizplease"]


@pytest.mark.asyncio
async def test_get_upcoming_always_includes_manual_events(db):
    await db.add_manual_event("Свой квиз", "Клуб", None, "2026-08-05", "20:00", None, added_by=1)

    filtered = await db.get_upcoming(date(2026, 8, 1), date(2026, 8, 31), {"quizplease"})
    assert [r[0] for r in filtered] == ["manual"]


@pytest.mark.asyncio
async def test_favorites_toggle_and_clear(db):
    chat_id = 42
    assert await db.get_favorites(chat_id) == set()

    await db.set_favorite(chat_id, "quizplease", True)
    await db.set_favorite(chat_id, "brainsurf", True)
    assert await db.get_favorites(chat_id) == {"quizplease", "brainsurf"}

    await db.set_favorite(chat_id, "quizplease", False)
    assert await db.get_favorites(chat_id) == {"brainsurf"}

    await db.clear_favorites(chat_id)
    assert await db.get_favorites(chat_id) == set()


@pytest.mark.asyncio
async def test_reminder_settings_roundtrip(db):
    chat_id = 7
    assert await db.get_reminder_minutes(chat_id) is None

    await db.set_reminder(chat_id, 180)
    assert await db.get_reminder_minutes(chat_id) == 180
    assert await db.get_all_reminder_settings() == [(chat_id, 180)]

    await db.set_reminder(chat_id, 60)
    assert await db.get_reminder_minutes(chat_id) == 60

    await db.clear_reminder(chat_id)
    assert await db.get_reminder_minutes(chat_id) is None


@pytest.mark.asyncio
async def test_reminder_candidates_and_sent_tracking(db):
    today = date(2026, 8, 5)
    await db.replace_source_events(
        "quizplease",
        [Event(source="quizplease", title="Игра А", event_date=today, event_time=time(19, 0))],
    )
    await db.add_manual_event("Свой квиз", "Клуб", None, today.isoformat(), "20:00", None, added_by=1)

    candidates = await db.get_reminder_candidates(today)
    sources = {row[0] for row in candidates}
    assert sources == {"quizplease", "manual"}

    dedup_key = next(row[7] for row in candidates if row[0] == "quizplease")
    assert await db.was_reminder_sent(1, dedup_key) is False

    await db.mark_reminder_sent(1, dedup_key, today.isoformat())
    assert await db.was_reminder_sent(1, dedup_key) is True
    # A different chat hasn't been notified yet.
    assert await db.was_reminder_sent(2, dedup_key) is False


@pytest.mark.asyncio
async def test_purge_old_events_also_clears_old_sent_reminders(db):
    await db.mark_reminder_sent(1, "quizplease|old", "2026-01-01")
    await db.mark_reminder_sent(1, "quizplease|new", "2026-08-05")

    await db.purge_old_events(date(2026, 8, 1))

    assert await db.was_reminder_sent(1, "quizplease|old") is False
    assert await db.was_reminder_sent(1, "quizplease|new") is True


@pytest.mark.asyncio
async def test_purge_old_events_also_clears_old_game_reminders(db):
    await db.toggle_game_reminder(1, "quizplease|old", "2026-01-01")
    await db.toggle_game_reminder(1, "quizplease|new", "2026-08-05")

    await db.purge_old_events(date(2026, 8, 1))

    assert await db.get_game_reminder_keys(1) == {"quizplease|new"}


@pytest.mark.asyncio
async def test_get_day_games_with_ids_returns_events_and_manual_with_dedup_keys(db):
    today = date(2026, 8, 5)
    await db.replace_source_events(
        "quizplease", [Event(source="quizplease", title="Игра А", event_date=today, event_time=time(19, 0))]
    )
    await db.add_manual_event("Свой квиз", "Клуб", None, today.isoformat(), "20:00", None, added_by=1)

    games = await db.get_day_games_with_ids(today)
    kinds = {row[0] for row in games}
    assert kinds == {"e", "m"}
    for row in games:
        assert row[7]  # dedup_key present for every row


@pytest.mark.asyncio
async def test_get_event_ref_and_manual_event_ref(db):
    today = date(2026, 8, 5)
    await db.replace_source_events(
        "quizplease", [Event(source="quizplease", title="Игра А", event_date=today, event_time=time(19, 0))]
    )
    await db.add_manual_event("Свой квиз", "Клуб", None, today.isoformat(), "20:00", None, added_by=1)

    games = await db.get_day_games_with_ids(today)
    event_id = next(row[1] for row in games if row[0] == "e")
    manual_id = next(row[1] for row in games if row[0] == "m")

    dedup_key, event_date, source, title, venue, event_time = await db.get_event_ref(event_id)
    assert (source, title, event_date) == ("quizplease", "Игра А", today.isoformat())

    manual_ref = await db.get_manual_event_ref(manual_id)
    assert manual_ref[0] == f"manual-{manual_id}"
    assert manual_ref[2:4] == ("manual", "Свой квиз")

    assert await db.get_event_ref(999999) is None
    assert await db.get_manual_event_ref(999999) is None


@pytest.mark.asyncio
async def test_toggle_game_reminder(db):
    chat_id = 5
    assert await db.get_game_reminder_keys(chat_id) == set()

    subscribed = await db.toggle_game_reminder(chat_id, "quizplease|a", "2026-08-05")
    assert subscribed is True
    assert await db.get_game_reminder_keys(chat_id) == {"quizplease|a"}

    subscribed = await db.toggle_game_reminder(chat_id, "quizplease|a", "2026-08-05")
    assert subscribed is False
    assert await db.get_game_reminder_keys(chat_id) == set()
