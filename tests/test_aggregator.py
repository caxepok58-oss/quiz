from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from bot.aggregator import _refresh_one
from bot.db import Database


class _FailingSource:
    name = "shakerquiz"

    async def fetch(self):
        raise RuntimeError("site is down")


class _WorkingSource:
    name = "shakerquiz"

    async def fetch(self):
        return []


@pytest_asyncio.fixture
async def db():
    database = Database(":memory:")
    await database.connect()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_no_alert_before_third_consecutive_failed_day(db):
    bot = AsyncMock()
    # Seed one prior failed day so the next real _refresh_one call lands on day 2.
    await db.set_source_status(_FailingSource.name, False, "boom", 0, today=date.today() - timedelta(days=1))

    await _refresh_one(db, _FailingSource(), bot, {111})

    assert bot.send_message.await_count == 0


@pytest.mark.asyncio
async def test_alerts_admins_on_third_consecutive_failed_day(db):
    bot = AsyncMock()
    # Seed two prior failed days so the next real _refresh_one call lands on day 3.
    await db.set_source_status(_FailingSource.name, False, "boom", 0, today=date.today() - timedelta(days=2))
    await db.set_source_status(_FailingSource.name, False, "boom", 0, today=date.today() - timedelta(days=1))

    await _refresh_one(db, _FailingSource(), bot, {111, 222})

    assert bot.send_message.await_count == 2
    sent_chat_ids = {call.args[0] for call in bot.send_message.await_args_list}
    assert sent_chat_ids == {111, 222}
    assert "3-й день подряд" in bot.send_message.await_args_list[0].args[1]


@pytest.mark.asyncio
async def test_no_alert_without_bot_or_admin_ids(db):
    # Two prior failed days - the 3rd would normally alert, but with no bot/admin_ids
    # to send through, _refresh_one must just skip sending instead of raising.
    await db.set_source_status(_FailingSource.name, False, "boom", 0, today=date.today() - timedelta(days=2))
    await db.set_source_status(_FailingSource.name, False, "boom", 0, today=date.today() - timedelta(days=1))

    await _refresh_one(db, _FailingSource(), None, None)


@pytest.mark.asyncio
async def test_recovery_resets_the_streak_so_alerting_can_happen_again(db):
    bot = AsyncMock()
    await db.set_source_status(_FailingSource.name, False, "boom", 0, today=date.today() - timedelta(days=2))
    await db.set_source_status(_FailingSource.name, False, "boom", 0, today=date.today() - timedelta(days=1))
    await _refresh_one(db, _FailingSource(), bot, {111})
    assert bot.send_message.await_count == 1

    bot.send_message.reset_mock()
    await _refresh_one(db, _WorkingSource(), bot, {111})
    assert bot.send_message.await_count == 0
