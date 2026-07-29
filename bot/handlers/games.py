from datetime import date, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db import Database
from ..formatting import build_messages
from ..keyboards import BTN_7_DAYS, BTN_30_DAYS

router = Router(name="games")


async def _send_games(message: Message, db: Database, city_name: str, days: int) -> None:
    today = date.today()
    rows = await db.get_upcoming(today, today + timedelta(days=days))
    for chunk in build_messages(rows, city_name, days):
        await message.answer(chunk)


@router.message(Command("games", "quizzes"))
async def cmd_games(message: Message, db: Database, city_name: str, lookahead_days: int) -> None:
    await _send_games(message, db, city_name, lookahead_days)


@router.message(F.text == BTN_7_DAYS)
async def btn_games_7_days(message: Message, db: Database, city_name: str) -> None:
    await _send_games(message, db, city_name, 7)


@router.message(F.text == BTN_30_DAYS)
async def btn_games_30_days(message: Message, db: Database, city_name: str) -> None:
    await _send_games(message, db, city_name, 30)
