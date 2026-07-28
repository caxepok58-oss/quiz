import re
from datetime import date, time

from bs4 import BeautifulSoup

from ..http_client import fetch_text
from ..models import Event
from ..text_parsing import find_date
from .base import BaseSource

# penza.mamaquiz.ru is built with Tilda (a page-builder): every field
# (title, description, venue, address, time, price) is its own absolutely
# positioned <div> with no shared wrapper per game, so there's no clean
# ".game-card" selector to key off - only reading order is reliable.
# Because of that, venue names are matched against a hardcoded list of the
# handful of bars that actually host quizzes in Penza (the same ones show
# up across quizplease/shakerquiz/brainsurf too) rather than parsed
# generically; add to _VENUES if MamaQuiz starts using a new venue.
_WEEKDAYS = "Понедельник|Вторник|Среда|Четверг|Пятница|Суббота|Воскресенье"
_VENUES = r"Harat'?s\s*Pub|Достоевский|Ламбада|Высота\s*175"
_TITLE_NUMBER_RE = re.compile(r".+?#\d+")
_RECORD_RE = re.compile(
    rf"(?:{_WEEKDAYS})\s+(?P<day>\d{{1,2}})\s+(?P<month>[а-яё]+)\s+"
    rf"(?P<title>.+?)\s+(?={_VENUES})"
    rf"(?P<venue>{_VENUES})\s*"
    r"(?P<address>ул\.[^\d]*\d+[а-яА-Я]?)\s*"
    r"(?P<time_h>[01]?\d|2[0-3]):(?P<time_m>[0-5]\d)\s*начало игры\s*"
    r"(?P<price>\d+)\s*руб\./чел\.",
    re.S,
)


class MamaQuizSource(BaseSource):
    name = "mamaquiz"
    url = "https://penza.mamaquiz.ru/"

    async def fetch(self) -> list[Event]:
        html = await fetch_text(self.url)
        return self.parse(html)

    def parse(self, html: str) -> list[Event]:
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ", strip=True)
        today = date.today()

        events = []
        for match in _RECORD_RE.finditer(text):
            event_date = find_date(f"{match['day']} {match['month']}", today)
            if event_date is None:
                continue
            events.append(
                Event(
                    source=self.name,
                    title=self._clean_title(match["title"]),
                    event_date=event_date,
                    event_time=time(int(match["time_h"]), int(match["time_m"])),
                    venue=re.sub(r"\s+", " ", match["venue"]).strip(),
                    address=match["address"].strip(),
                    price=match["price"],
                    url=self.url,
                )
            )
        return events

    @staticmethod
    def _clean_title(raw: str) -> str:
        numbered = _TITLE_NUMBER_RE.match(raw)
        if numbered:
            return numbered.group(0).strip()
        return raw[:50].rsplit(" ", 1)[0].strip()
