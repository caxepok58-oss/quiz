from datetime import date, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from ..db import Database
from ..formatting import build_messages
from ..keyboards import BTN_7_DAYS, BTN_30_DAYS, BTN_SCHEDULE_IMAGE
from ..schedule_image import render_schedule_image

router = Router(name="games")

_IMAGE_DAYS = 30


async def _send_games(message: Message, db: Database, city_name: str, days: int) -> None:
    today = date.today()
    favorites = await db.get_favorites(message.chat.id)
    rows = await db.get_upcoming(today, today + timedelta(days=days), favorites or None)
    updated_at = await db.get_last_successful_update()
    for chunk in build_messages(rows, city_name, days, updated_at):
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


@router.message(Command("schedule_image"))
@router.message(F.text == BTN_SCHEDULE_IMAGE)
async def btn_schedule_image(message: Message, db: Database, city_name: str) -> None:
    await message.answer("Генерирую картинку с расписанием…")
    today = date.today()
    rows = await db.get_upcoming(today, today + timedelta(days=_IMAGE_DAYS))  # full schedule, all franchises
    if not rows:
        await message.answer(f"На ближайшие {_IMAGE_DAYS} дней в г. {city_name} игр не найдено.")
        return
    updated_at = await db.get_last_successful_update()
    image_bytes = render_schedule_image(rows, city_name, _IMAGE_DAYS, updated_at)
    photo = BufferedInputFile(image_bytes, filename="schedule.jpg")
    await message.answer_photo(photo, caption=f"Полное расписание квизов в г. {city_name} на {_IMAGE_DAYS} дней")
