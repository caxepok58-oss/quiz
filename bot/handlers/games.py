from datetime import date, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db import Database
from ..formatting import build_messages

router = Router(name="games")


@router.message(Command("games", "quizzes"))
async def cmd_games(message: Message, db: Database, city_name: str, lookahead_days: int) -> None:
    today = date.today()
    rows = await db.get_upcoming(today, today + timedelta(days=lookahead_days))
    for chunk in build_messages(rows, city_name, lookahead_days):
        await message.answer(chunk)
