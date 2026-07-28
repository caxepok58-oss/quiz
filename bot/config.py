import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> set[int]:
    return {int(x) for x in raw.split(",") if x.strip()}


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int]
    city_name: str
    timezone: str
    lookahead_days: int
    scrape_hour: int
    db_path: str
    proxy_url: str | None


def load_config() -> Config:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
    return Config(
        bot_token=token,
        admin_ids=_parse_admin_ids(os.environ.get("ADMIN_IDS", "")),
        city_name=os.environ.get("CITY_NAME", "Пенза"),
        timezone=os.environ.get("TZ_NAME", "Europe/Moscow"),
        lookahead_days=int(os.environ.get("LOOKAHEAD_DAYS", "30")),
        scrape_hour=int(os.environ.get("SCRAPE_HOUR", "6")),
        db_path=os.environ.get("DB_PATH", "quizzes.db"),
        proxy_url=os.environ.get("BOT_PROXY_URL") or None,
    )
