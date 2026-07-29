from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from ..aggregator import refresh_all
from ..db import Database
from ..keyboards import BTN_UPDATE

router = Router(name="admin")

_ADD_GAME_HELP = (
    "Формат:\n"
    "/add_game ГГГГ-ММ-ДД ЧЧ:ММ Название игры | Место | Цена\n\n"
    "Пример:\n"
    '/add_game 2026-08-05 19:00 Квиз про кино | Бар "Огни" | 500'
)


def _is_admin(user_id: int, admin_ids: set[int]) -> bool:
    return user_id in admin_ids


@router.message(Command("update"))
async def cmd_update(message: Message, db: Database, admin_ids: set[int]) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return
    await message.answer("Обновляю расписание из источников…")
    await refresh_all(db)
    await message.answer("Готово. /sources — посмотреть статус.")


@router.message(F.text == BTN_UPDATE)
async def btn_update(message: Message, db: Database, admin_ids: set[int]) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        await message.answer("Обновление данных доступно только администраторам.")
        return
    await message.answer("Обновляю расписание из источников…")
    await refresh_all(db)
    await message.answer("Готово. /sources — посмотреть статус.")


@router.message(Command("sources"))
async def cmd_sources(message: Message, db: Database) -> None:
    rows = await db.get_source_statuses()
    if not rows:
        await message.answer("Пока нет данных ни по одному источнику.")
        return
    lines = ["Статус источников:"]
    for source, ok, msg, count, updated_at in rows:
        if ok:
            lines.append(f"✅ {source}: {count} игр, обновлено {updated_at} UTC")
        else:
            lines.append(f"⚠️ {source}: данные недоступны, нет расписания")
    await message.answer("\n".join(lines))


@router.message(Command("add_game"))
async def cmd_add_game(message: Message, db: Database, admin_ids: set[int]) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        await message.answer("Команда доступна только администраторам.")
        return
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer(_ADD_GAME_HELP)
        return
    _, date_part, time_part, rest = parts
    fields = [f.strip() for f in rest.split("|")]
    try:
        event_date = date.fromisoformat(date_part)
    except ValueError:
        await message.answer(_ADD_GAME_HELP)
        return
    title = fields[0]
    venue = fields[1] if len(fields) > 1 and fields[1] else None
    price = fields[2] if len(fields) > 2 and fields[2] else None
    await db.add_manual_event(title, venue, None, event_date.isoformat(), time_part, price, message.from_user.id)
    await message.answer(f"Добавлено: {event_date.isoformat()} {time_part} — {title}")


@router.message(Command("list_manual"))
async def cmd_list_manual(message: Message, db: Database, admin_ids: set[int]) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return
    rows = await db.list_manual_events()
    if not rows:
        await message.answer("Ручных записей нет.")
        return
    lines = [f"#{r[0]} {r[4]} {r[5] or ''} — {r[1]} ({r[2] or '—'})" for r in rows]
    await message.answer("\n".join(lines))


@router.message(Command("del_game"))
async def cmd_del_game(message: Message, db: Database, admin_ids: set[int]) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Используйте: /del_game <id> (см. /list_manual)")
        return
    ok = await db.delete_manual_event(int(parts[1]))
    await message.answer("Удалено." if ok else "Запись не найдена.")
