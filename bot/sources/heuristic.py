"""Best-effort schedule scraper.

This bot was built in a sandbox with no outbound internet access, so the
real markup of the target quiz-schedule pages could not be inspected to
write exact CSS selectors. Instead of hardcoding brittle guesses, this
scraper scans rendered text for recognizable Russian date/time patterns
and expands to the smallest enclosing block as one "game card".

Once this runs somewhere with real network access, use the /sources admin
command to see how many events each source finds. If a source returns 0,
inspect its page HTML and either tighten CARD_TAGS/MAX_CARD_LEN below or
give that source's subclass a dedicated parser.
"""
import logging
from datetime import date

from bs4 import BeautifulSoup
from bs4.element import Tag

from ..http_client import fetch_text
from ..models import Event
from ..text_parsing import count_dates, find_date, find_time
from .base import BaseSource

logger = logging.getLogger(__name__)

CARD_TAGS = ("div", "li", "article", "tr")
MAX_CARD_TEXT_LEN = 600


class HeuristicScheduleSource(BaseSource):
    def __init__(self, name: str, url: str, default_venue: str | None = None):
        self.name = name
        self.url = url
        self.default_venue = default_venue

    async def fetch(self) -> list[Event]:
        html = await fetch_text(self.url)
        return self.parse(html)

    def parse(self, html: str) -> list[Event]:
        soup = BeautifulSoup(html, "lxml")
        today = date.today()
        seen: dict[int, tuple[Event, str]] = {}

        for tag in soup.find_all(CARD_TAGS):
            text = tag.get_text(" ", strip=True)
            if not text or len(text) > MAX_CARD_TEXT_LEN:
                continue
            if find_date(text, today) is None:
                continue

            card = self._expand_to_card(tag)
            if id(card) in seen:
                continue

            card_text = card.get_text(" ", strip=True)
            if count_dates(card_text) != 1:
                # Expansion swallowed a neighboring card's date too (or this
                # tag is itself a container wrapping several games) - the
                # text can no longer be attributed to a single game.
                continue
            event_date = find_date(card_text, today)
            if event_date is None:
                continue

            event = Event(
                source=self.name,
                title=self._guess_title(card, card_text),
                event_date=event_date,
                event_time=find_time(card_text),
                venue=self.default_venue,
                url=self.url,
            )
            seen[id(card)] = (event, card_text)

        events = self._drop_nested_duplicates(list(seen.values()))
        return self._dedup(events)

    @staticmethod
    def _expand_to_card(tag: Tag, max_levels: int = 3) -> Tag:
        """Walk a few levels up so the card includes sibling fields
        (title/venue/price) that usually sit next to the date, not inside
        the same leaf element as it."""
        node = tag
        for _ in range(max_levels):
            parent = node.parent
            if parent is None or parent.name in ("body", "html", "[document]"):
                break
            if count_dates(parent.get_text(" ", strip=True)) != 1:
                # Ascending further would merge in a sibling card's date.
                break
            node = parent
        return node

    @staticmethod
    def _guess_title(card: Tag, card_text: str) -> str:
        heading = card.find(["h1", "h2", "h3", "h4", "b", "strong"])
        if heading and heading.get_text(strip=True):
            return heading.get_text(strip=True)[:120]
        return card_text[:120]

    @staticmethod
    def _drop_nested_duplicates(events_with_text: list[tuple[Event, str]]) -> list[Event]:
        """Card expansion can independently latch onto more than one DOM node
        for the same real game - e.g. a heading that itself embeds the date
        ("...играем 29 июля, 19:30...") next to the actual date/venue block,
        each becoming its own small "card". A franchise doesn't run two
        different games at the exact same date and time on one schedule
        page, so when several cards share both, they're the same game seen
        twice - keep only the one with the longest captured text (the
        fullest, most complete card)."""
        groups: dict[tuple, list[tuple[Event, str]]] = {}
        kept: list[Event] = []
        for event, text in events_with_text:
            if event.event_time is None:
                kept.append(event)
                continue
            groups.setdefault((event.event_date, event.event_time), []).append((event, text))

        for group in groups.values():
            best_event, _ = max(group, key=lambda pair: len(pair[1]))
            kept.append(best_event)
        return kept

    @staticmethod
    def _dedup(events: list[Event]) -> list[Event]:
        by_key: dict[str, Event] = {}
        for ev in events:
            by_key[ev.dedup_key()] = ev
        return list(by_key.values())
