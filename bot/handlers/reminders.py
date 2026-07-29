from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db import Database

router = Router(name="reminders")

_DEFAULT_HOURS = 3
_MIN_HOURS = 1
_MAX_HOURS = 24

_HELP = (
    "/remind_on [часов] — включить напоминания перед игрой (по умолчанию за 3 часа, "
    f"можно от {_MIN_HOURS} до {_MAX_HOURS}).\n"
    "/remind_off — выключить напоминания.\n\n"
    "Если в /favorites отмечены франшизы, напоминания приходят только по ним — "
    "иначе по всем играм."
)


@router.message(Command("remind_on"))
async def cmd_remind_on(message: Message, db: Database) -> None:
    parts = message.text.split(maxsplit=1)
    hours = _DEFAULT_HOURS
    if len(parts) > 1:
        try:
            hours = int(parts[1].strip())
        except ValueError:
            await message.answer(_HELP)
            return
    hours = max(_MIN_HOURS, min(_MAX_HOURS, hours))
    await db.set_reminder(message.chat.id, hours * 60)
    await message.answer(f"🔔 Напоминания включены: за {hours} ч. до начала игры. /remind_off — выключить.")


@router.message(Command("remind_off"))
async def cmd_remind_off(message: Message, db: Database) -> None:
    await db.clear_reminder(message.chat.id)
    await message.answer("🔕 Напоминания выключены.")


@router.message(Command("remind_status", "remind"))
async def cmd_remind_status(message: Message, db: Database) -> None:
    minutes = await db.get_reminder_minutes(message.chat.id)
    if minutes is None:
        await message.answer(f"🔕 Напоминания выключены.\n\n{_HELP}")
        return
    await message.answer(f"🔔 Напоминания включены: за {minutes // 60} ч. до начала игры.\n\n{_HELP}")
