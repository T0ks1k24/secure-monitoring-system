from abc import ABC, abstractmethod
from domain.entities.event import SecurityEvent
from typing import List


class EventRepository(ABC):

    @abstractmethod
    def save(self, event: SecurityEvent) -> SecurityEvent:
        pass

    @abstractmethod
    def get_by_id(self, event_id: str) -> SecurityEvent | None:
        pass

    @abstractmethod
    def get_all(self) -> List[SecurityEvent]:
        pass
