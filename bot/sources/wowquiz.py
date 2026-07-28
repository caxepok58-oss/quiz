import json
from datetime import datetime

from ..http_client import fetch_text
from ..models import Event
from .base import BaseSource

# api.etowow.ru is a shared multi-tenant backend used by many local
# "Wow Quiz"-branded franchises across different cities - GET /games/all
# returns every city's games mixed together unless you pass a "domain"
# query param matching a franchise's registered domain exactly (found by
# reading the minified Nuxt bundle: every request goes through an
# onRequest hook that injects `domain: window.location.origin`). Penza's
# franchise (id 206) is registered under domain "https://pnz.wowquiz.ru".
_API_URL = "https://api.etowow.ru/games/all"
_PENZA_DOMAIN = "https://pnz.wowquiz.ru"


class WowQuizSource(BaseSource):
    name = "wowquiz"
    url = "https://pnz.wowquiz.ru/schedule"

    async def fetch(self) -> list[Event]:
        games: list[dict] = []
        page = 1
        while True:
            payload = json.loads(
                await fetch_text(
                    _API_URL,
                    params={"upcoming": "1", "page": str(page), "domain": _PENZA_DOMAIN},
                )
            )
            data = payload.get("data") or {}
            batch = data.get("games") or []
            games.extend(batch)
            page_count = data.get("pageCount") or 1
            if not batch or page >= page_count:
                break
            page += 1
        return self.parse(games)

    def parse(self, games: list[dict]) -> list[Event]:
        events = []
        for game in games:
            raw_date = game.get("date")
            if not raw_date:
                continue
            try:
                dt = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            bar = game.get("bar") or {}
            events.append(
                Event(
                    source=self.name,
                    title=game.get("title") or "Вау Квиз",
                    event_date=dt.date(),
                    event_time=dt.time(),
                    venue=bar.get("title"),
                    address=bar.get("address"),
                    price=str(game["price"]) if game.get("price") is not None else None,
                    url=self.url,
                )
            )
        return events
