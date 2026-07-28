from dataclasses import dataclass
from datetime import date, time


@dataclass
class Event:
    source: str
    title: str
    event_date: date
    event_time: time | None = None
    venue: str | None = None
    address: str | None = None
    price: str | None = None
    url: str | None = None

    def dedup_key(self) -> str:
        return "|".join(
            [
                self.source,
                self.title.strip().lower(),
                self.event_date.isoformat(),
                self.event_time.strftime("%H:%M") if self.event_time else "",
                (self.venue or "").strip().lower(),
            ]
        )
