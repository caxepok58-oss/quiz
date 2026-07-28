from abc import ABC, abstractmethod

from ..models import Event


class BaseSource(ABC):
    name: str

    @abstractmethod
    async def fetch(self) -> list[Event]:
        """Return upcoming events found on this source."""
