from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from ..keyboards import main_menu_keyboard

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, city_name: str) -> None:
    await message.answer(
        f"Привет! Я собираю расписание квизов в г. {city_name} на месяц вперёд "
        f"и обновляю его раз в сутки.\n\n"
        f"Кнопки ниже — быстрый доступ к расписанию, либо команды:\n"
        f"/games — список ближайших игр\n"
        f"/favorites — выбрать интересные франшизы (фильтрует /games)\n"
        f"/remind_games — выбрать конкретные игры для напоминания\n"
        f"/remind_on, /remind_off — включить/выключить напоминания\n"
        f"/sources — статус источников данных",
        reply_markup=main_menu_keyboard(),
    )
