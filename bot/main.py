import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .aggregator import refresh_all
from .config import load_config
from .db import Database
from .handlers import admin, common, games
from .scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    config = load_config()

    db = Database(config.db_path)
    await db.connect()

    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(common.router)
    dp.include_router(games.router)
    dp.include_router(admin.router)

    dp["db"] = db
    dp["city_name"] = config.city_name
    dp["lookahead_days"] = config.lookahead_days
    dp["admin_ids"] = config.admin_ids

    logger.info("Running initial schedule refresh")
    await refresh_all(db)
    scheduler = setup_scheduler(db, config.scrape_hour, config.timezone)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
