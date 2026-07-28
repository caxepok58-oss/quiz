import json
from datetime import datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from ..http_client import fetch_text
from ..models import Event
from .base import BaseSource

# The site (penza.shakerquiz.ru) is a Next.js app that server-renders its
# own API responses into a <script id="__NEXT_DATA__"> JSON blob
# (props.pageProps.store: a list of [endpoint, payload] pairs, e.g.
# "GET/games/search" and "GET/games/venue/:venue/search"). That's exactly
# the schedule data we need, already scoped to Penza - no separate API
# call required, just parse that one script tag.
#
# `event_time` is ISO-8601 with a "Z" (UTC) suffix. We convert it to
# Europe/Moscow for display, taking the "Z" at face value; this hasn't
# been cross-checked against a human-readable time shown elsewhere on the
# site (there wasn't one in the static HTML). If real games turn out to
# start at the raw UTC-labelled clock time instead, drop the
# .astimezone(_MOSCOW) conversion below.
_MOSCOW = ZoneInfo("Europe/Moscow")
_GAMES_KEY = "GET/games/search"
_VENUES_KEY = "GET/games/venue/:venue/search"


class ShakerQuizSource(BaseSource):
    name = "shakerquiz"
    url = "https://penza.shakerquiz.ru/"

    async def fetch(self) -> list[Event]:
        html = await fetch_text(self.url)
        return self.parse(html)

    def parse(self, html: str) -> list[Event]:
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            return []
        data = json.loads(script.string)
        store = (data.get("props") or {}).get("pageProps", {}).get("store") or []

        games_by_id: dict[str, dict] = {}
        venue_by_game_id: dict[str, dict] = {}
        for entry in store:
            if not isinstance(entry, list) or len(entry) != 2:
                continue
            key, items = entry
            if key == _GAMES_KEY and isinstance(items, list):
                games_by_id = {g["id"]: g for g in items if g.get("id")}
            elif key == _VENUES_KEY and isinstance(items, list):
                venue_by_game_id = {v["game_id"]: v for v in items if v.get("game_id")}

        events = []
        for game_id, game in games_by_id.items():
            if game.get("status") == "Finish" or game.get("visibility") != "Visible":
                continue
            raw_time = game.get("event_time")
            if not raw_time:
                continue
            try:
                dt_local = datetime.fromisoformat(raw_time.replace("Z", "+00:00")).astimezone(_MOSCOW)
            except ValueError:
                continue

            venue = venue_by_game_id.get(game_id) or {}
            address = " ".join(filter(None, [venue.get("street"), venue.get("house_number")])) or None

            events.append(
                Event(
                    source=self.name,
                    title=game.get("name") or f"Шейкер квиз №{game.get('number')}",
                    event_date=dt_local.date(),
                    event_time=dt_local.time(),
                    venue=venue.get("name"),
                    address=address,
                    price=str(game["price"]) if game.get("price") is not None else None,
                    url=self.url,
                )
            )
        return events
