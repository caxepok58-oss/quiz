from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from .formatting import FRANCHISE_KEYS, franchise_color, franchise_name

BTN_UPDATE = "🔄 Обновить данные"
BTN_7_DAYS = "📅 Ближайшие игры на 7 дней"
BTN_30_DAYS = "🗓 Ближайшие игры на 30 дней"
BTN_FAVORITES = "⭐ Мои франшизы"
BTN_REMIND_GAMES = "🔔 Выбрать игры для напоминания"
BTN_REMIND_ON = "🔔 Включить напоминания"
BTN_REMIND_OFF = "🔕 Выключить напоминания"
BTN_SCHEDULE_IMAGE_30 = "🖼 Сгенерировать расписание на 30 дней"
BTN_SCHEDULE_IMAGE_7 = "🖼 Сгенерировать расписание на неделю"
BTN_SCHEDULE_IMAGE_14 = "🖼 Сгенерировать расписание на 2 недели"

_FAV_PREFIX = "fav:"
_FAV_CLEAR = "fav:clear"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_7_DAYS), KeyboardButton(text=BTN_30_DAYS)],
            [KeyboardButton(text=BTN_FAVORITES), KeyboardButton(text=BTN_UPDATE)],
            [KeyboardButton(text=BTN_REMIND_GAMES)],
            [KeyboardButton(text=BTN_REMIND_ON), KeyboardButton(text=BTN_REMIND_OFF)],
            [KeyboardButton(text=BTN_SCHEDULE_IMAGE_7), KeyboardButton(text=BTN_SCHEDULE_IMAGE_14)],
            [KeyboardButton(text=BTN_SCHEDULE_IMAGE_30)],
        ],
        resize_keyboard=True,
    )


def favorites_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    rows = []
    for source in FRANCHISE_KEYS:
        mark = "✅" if source in selected else "⬜"
        label = f"{mark} {franchise_color(source)} {franchise_name(source)}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"{_FAV_PREFIX}{source}")])
    rows.append([InlineKeyboardButton(text="🔄 Показывать все франшизы", callback_data=_FAV_CLEAR)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def game_picker_keyboard(games: list[tuple], picked: set[str], day_offset: int, max_offset: int) -> InlineKeyboardMarkup:
    """games: rows from Database.get_day_games_with_ids (kind, id, source, title, venue, event_time, price, dedup_key)."""
    rows = []
    for kind, event_id, source, title, _venue, event_time, _price, dedup_key in games:
        mark = "✅" if dedup_key in picked else "⬜"
        label = f"{mark} {event_time or '??:??'} {franchise_color(source)} {_truncate(title, 22)}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"rg:{kind}:{event_id}:{day_offset}")])

    nav = []
    if day_offset > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"rg:day:{day_offset - 1}"))
    nav.append(InlineKeyboardButton(text=f"День {day_offset + 1}", callback_data="rg:noop"))
    if day_offset < max_offset:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"rg:day:{day_offset + 1}"))
    rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)
