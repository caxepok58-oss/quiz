import json
from datetime import datetime

from ..http_client import fetch_text
from ..models import Event
from .base import BaseSource

# The site (penza.quizplease.ru) is a Nuxt SPA that fetches its schedule
# client-side from this JSON API - no HTML scraping needed. Found by
# downloading the /schedule route's lazy JS chunk and grepping it for
# `$fetch(`: it calls `api/games/schedule/${cityId}` against
# baseURL "https://api.quizplease.ru". Penza's numeric city id (85) came
# from the "cities" list embedded in the page's Nuxt payload
# (window.__NUXT__, keyed by slug "penza"). No auth header is required for
# this endpoint (unlike e.g. /api/cities, which 401s).
_API_URL = "https://api.quizplease.ru/api/games/schedule/{city_id}"
_PENZA_CITY_ID = 85


class QuizPleaseSource(BaseSource):
    name = "quizplease"
    url = "https://penza.quizplease.ru/schedule"

    def __init__(self, city_id: int = _PENZA_CITY_ID):
        self.city_id = city_id

    async def fetch(self) -> list[Event]:
        text = await fetch_text(
            _API_URL.format(city_id=self.city_id),
            params={"per_page": "100", "order": "date"},
        )
        return self.parse(json.loads(text))

    def parse(self, payload: dict) -> list[Event]:
        games = (payload.get("data") or {}).get("data") or []
        events = []
        for game in games:
            raw_date = game.get("date")
            if not raw_date:
                continue
            try:
                dt = datetime.strptime(raw_date, "%d.%m.%Y %H:%M")
            except ValueError:
                continue
            place = game.get("place") or {}
            events.append(
                Event(
                    source=self.name,
                    title=(game.get("title") or "Квиз, плиз!").strip(),
                    event_date=dt.date(),
                    event_time=dt.time(),
                    venue=place.get("title"),
                    address=place.get("address"),
                    price=str(game["price"]) if game.get("price") is not None else None,
                    url=self.url,
                )
            )
        return events
