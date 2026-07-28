from abc import ABC, abstractmethod

import aiohttp

from ..models import Event


class BaseSource(ABC):
    name: str

    @abstractmethod
    async def fetch(self, session: aiohttp.ClientSession) -> list[Event]:
        """Return upcoming events found on this source's page."""
