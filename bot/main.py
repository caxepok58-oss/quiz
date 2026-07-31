import asyncio
import logging
import socket

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from .aggregator import refresh_all
from .config import load_config
from .db import Database
from .handlers import admin, common, favorites, games, reminders
from .middlewares import UserTrackingMiddleware
from .scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class _IPv4AiohttpSession(AiohttpSession):
    """Forces IPv4 for the Telegram API connection.

    On some Windows setups, aiohttp's default connector tries IPv6 to
    api.telegram.org and hangs with "ClientConnectorError ... semaphore
    timeout" even though IPv4 connectivity (curl, Telegram Desktop) works
    fine. Restricting the connector to AF_INET avoids that path entirely.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._connector_init["family"] = socket.AF_INET


async def main() -> None:
    config = load_config()

    db = Database(config.db_path)
    await db.connect()

    bot = Bot(
        token=config.bot_token,
        session=_IPv4AiohttpSession(proxy=config.proxy_url),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.update.outer_middleware(UserTrackingMiddleware(db))
    dp.include_router(common.router)
    dp.include_router(games.router)
    dp.include_router(favorites.router)
    dp.include_router(reminders.router)
    dp.include_router(admin.router)

    dp["db"] = db
    dp["city_name"] = config.city_name
    dp["lookahead_days"] = config.lookahead_days
    dp["admin_ids"] = config.admin_ids

    logger.info("Running initial schedule refresh")
    await refresh_all(db, bot, config.admin_ids)
    scheduler = setup_scheduler(db, bot, config.scrape_hour, config.timezone, config.admin_ids)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
