from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_UPDATE = "🔄 Обновить данные"
BTN_7_DAYS = "📅 Ближайшие игры на 7 дней"
BTN_30_DAYS = "🗓 Ближайшие игры на 30 дней"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_7_DAYS), KeyboardButton(text=BTN_30_DAYS)],
            [KeyboardButton(text=BTN_UPDATE)],
        ],
        resize_keyboard=True,
    )
