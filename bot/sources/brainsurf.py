from datetime import date

from bs4 import BeautifulSoup

from ..http_client import fetch_text
from ..models import Event
from ..text_parsing import find_date, find_time
from .base import BaseSource

# Plain server-rendered WordPress site (penza.brainsurf.ru, redirected from
# brainsurf.ru/penza/). Each game is a ".schedule-item" card with clean,
# stable classes - no SPA/API involved, so this is exact selector-based
# parsing rather than the heuristic text scanner. The swiper carousel
# duplicates each card for its loop effect, hence the dedup at the end.


class BrainSurfSource(BaseSource):
    name = "brainsurf"
    url = "https://penza.brainsurf.ru/"

    async def fetch(self) -> list[Event]:
        html = await fetch_text(self.url)
        return self.parse(html)

    def parse(self, html: str) -> list[Event]:
        soup = BeautifulSoup(html, "lxml")
        today = date.today()
        events = []

        for card in soup.select(".schedule-item"):
            title_tag = card.select_one(".schedule-item__title")
            date_tag = card.select_one(".src-date_time")
            if not title_tag or not date_tag:
                continue
            date_text = date_tag.get_text(strip=True)
            event_date = find_date(date_text, today)
            if event_date is None:
                continue

            location_tag = card.select_one(".schedule-icon--location")
            venue = None
            if location_tag:
                location_text = location_tag.get_text(strip=True)
                _city, _, rest = location_text.partition(",")
                venue = rest.strip() or location_text

            price_tag = card.select_one(".schedule-icon--price")
            price = None
            if price_tag:
                digits = "".join(ch for ch in price_tag.get_text() if ch.isdigit())
                price = digits or None

            events.append(
                Event(
                    source=self.name,
                    title=title_tag.get_text(strip=True),
                    event_date=event_date,
                    event_time=find_time(date_text),
                    venue=venue,
                    price=price,
                    url=self.url,
                )
            )

        by_key = {ev.dedup_key(): ev for ev in events}
        return list(by_key.values())
