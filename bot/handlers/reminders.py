from datetime import date, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ..db import Database
from ..formatting import format_date_header
from ..keyboards import game_picker_keyboard

router = Router(name="reminders")

_DEFAULT_HOURS = 3
_MIN_HOURS = 1
_MAX_HOURS = 24
_DEFAULT_LEAD_MINUTES = _DEFAULT_HOURS * 60

_HELP = (
    "/remind_games — выбрать конкретные игры, о которых напомнить (по дням, с кнопками).\n"
    "/remind_on [часов] — за сколько часов до игры напоминать (по умолчанию 3, "
    f"можно от {_MIN_HOURS} до {_MAX_HOURS}).\n"
    "/remind_off — выключить все напоминания (выбранные игры при этом сохранятся).\n\n"
    "Напоминание приходит только по играм, которые вы отметили в /remind_games."
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
    await message.answer(
        f"🔔 Напоминания включены: за {hours} ч. до начала игры.\n"
        f"Не забудьте выбрать сами игры через /remind_games — иначе напоминать не о чем."
    )


@router.message(Command("remind_off"))
async def cmd_remind_off(message: Message, db: Database) -> None:
    await db.clear_reminder(message.chat.id)
    await message.answer("🔕 Напоминания выключены. Выбранные игры сохранены — /remind_on включит напоминания снова.")


@router.message(Command("remind_status", "remind"))
async def cmd_remind_status(message: Message, db: Database) -> None:
    minutes = await db.get_reminder_minutes(message.chat.id)
    picked = await db.get_game_reminder_keys(message.chat.id)
    if minutes is None:
        status = "🔕 Напоминания выключены."
    else:
        status = f"🔔 Напоминания включены: за {minutes // 60} ч. до начала игры."
    await message.answer(f"{status}\nВыбрано игр: {len(picked)}.\n\n{_HELP}")


async def _render_picker(db: Database, chat_id: int, day_offset: int, lookahead_days: int):
    day = date.today() + timedelta(days=day_offset)
    favorites = await db.get_favorites(chat_id)
    games = await db.get_day_games_with_ids(day, favorites or None)
    picked = await db.get_game_reminder_keys(chat_id)

    text = f"🔔 Выберите игры для напоминания\n<b>{format_date_header(day)}</b>"
    if not games:
        text += "\n\nВ этот день игр не найдено."
    markup = game_picker_keyboard(games, picked, day_offset, max_offset=lookahead_days - 1)
    return text, markup


@router.message(Command("remind_games"))
async def cmd_remind_games(message: Message, db: Database, lookahead_days: int) -> None:
    text, markup = await _render_picker(db, message.chat.id, day_offset=0, lookahead_days=lookahead_days)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "rg:noop")
async def cb_remind_games_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("rg:day:"))
async def cb_remind_games_page(callback: CallbackQuery, db: Database, lookahead_days: int) -> None:
    day_offset = int(callback.data.removeprefix("rg:day:"))
    text, markup = await _render_picker(db, callback.message.chat.id, day_offset, lookahead_days)
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("rg:"))
async def cb_remind_games_toggle(callback: CallbackQuery, db: Database, lookahead_days: int) -> None:
    _, kind, event_id_str, day_offset_str = callback.data.split(":")
    event_id = int(event_id_str)
    day_offset = int(day_offset_str)
    chat_id = callback.message.chat.id

    ref = await (db.get_event_ref(event_id) if kind == "e" else db.get_manual_event_ref(event_id))
    if not ref:
        await callback.answer("Эта игра больше не в расписании.")
        return
    dedup_key, event_date, *_rest = ref

    subscribed = await db.toggle_game_reminder(chat_id, dedup_key, event_date)
    if subscribed and await db.get_reminder_minutes(chat_id) is None:
        await db.set_reminder(chat_id, _DEFAULT_LEAD_MINUTES)

    text, markup = await _render_picker(db, chat_id, day_offset, lookahead_days)
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer("Напомню перед игрой" if subscribed else "Напоминание снято")
