from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, city_name: str) -> None:
    await message.answer(
        f"Привет! Я собираю расписание квизов в г. {city_name} на месяц вперёд "
        f"и обновляю его раз в сутки.\n\n"
        f"Команды:\n"
        f"/games — список ближайших игр\n"
        f"/sources — статус источников данных"
    )
