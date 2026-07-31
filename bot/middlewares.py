from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from .db import Database


class UserTrackingMiddleware(BaseMiddleware):
    """Records first/last activity of every chat that talks to the bot, for /stats."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        chat = data.get("event_chat")
        if chat is not None:
            await self._db.touch_user(chat.id)
        return await handler(event, data)
