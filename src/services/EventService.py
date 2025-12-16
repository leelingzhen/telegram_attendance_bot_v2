from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from models.models import Event


class EventServicing(ABC):
    @abstractmethod
    async def fetch_events(self, from_date: datetime) -> List[Event]:
        pass
