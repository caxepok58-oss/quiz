from .base import BaseSource


class UnavailableSource(BaseSource):
    """A source with no working scraper yet.

    fetch() always raises, so the aggregator records the reason in
    source_status (visible via /sources) instead of silently reporting
    "0 games" - which would be indistinguishable from a real empty
    schedule. Use /add_game to add this organizer's games by hand until
    someone writes a real scraper for it.
    """

    def __init__(self, name: str, reason: str):
        self.name = name
        self._reason = reason

    async def fetch(self):
        raise RuntimeError(self._reason)
