from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ..db import Database
from ..formatting import FRANCHISE_KEYS, franchise_name
from ..keyboards import BTN_FAVORITES, favorites_keyboard

router = Router(name="favorites")


def _status_text(selected: set[str]) -> str:
    if not selected:
        return "Сейчас показываются игры всех франшиз."
    names = ", ".join(franchise_name(s) for s in FRANCHISE_KEYS if s in selected)
    return f"Сейчас показываются только: {names}."


async def _send_favorites(message: Message, db: Database) -> None:
    selected = await db.get_favorites(message.chat.id)
    text = (
        "⭐ Отметьте франшизы, игры которых вам интересны — /games и кнопки "
        "расписания будут показывать только их.\n\n" + _status_text(selected)
    )
    await message.answer(text, reply_markup=favorites_keyboard(selected))


@router.message(Command("favorites"))
async def cmd_favorites(message: Message, db: Database) -> None:
    await _send_favorites(message, db)


@router.message(F.text == BTN_FAVORITES)
async def btn_favorites(message: Message, db: Database) -> None:
    await _send_favorites(message, db)


@router.callback_query(F.data == "fav:clear")
async def cb_favorites_clear(callback: CallbackQuery, db: Database) -> None:
    await db.clear_favorites(callback.message.chat.id)
    selected: set[str] = set()
    await callback.message.edit_reply_markup(reply_markup=favorites_keyboard(selected))
    await callback.answer("Показываю игры всех франшиз")


@router.callback_query(F.data.startswith("fav:"))
async def cb_favorites_toggle(callback: CallbackQuery, db: Database) -> None:
    source = callback.data.removeprefix("fav:")
    if source not in FRANCHISE_KEYS:
        await callback.answer()
        return
    selected = await db.get_favorites(callback.message.chat.id)
    enabled = source not in selected
    await db.set_favorite(callback.message.chat.id, source, enabled)
    selected = await db.get_favorites(callback.message.chat.id)
    await callback.message.edit_reply_markup(reply_markup=favorites_keyboard(selected))
    await callback.answer(f"{franchise_name(source)}: {'добавлено' if enabled else 'убрано'}")
