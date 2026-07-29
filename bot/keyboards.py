from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from .formatting import FRANCHISE_KEYS, franchise_color, franchise_name

BTN_UPDATE = "🔄 Обновить данные"
BTN_7_DAYS = "📅 Ближайшие игры на 7 дней"
BTN_30_DAYS = "🗓 Ближайшие игры на 30 дней"
BTN_FAVORITES = "⭐ Мои франшизы"

_FAV_PREFIX = "fav:"
_FAV_CLEAR = "fav:clear"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_7_DAYS), KeyboardButton(text=BTN_30_DAYS)],
            [KeyboardButton(text=BTN_FAVORITES), KeyboardButton(text=BTN_UPDATE)],
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
