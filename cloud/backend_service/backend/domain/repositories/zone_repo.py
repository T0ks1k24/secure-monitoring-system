from abc import ABC, abstractmethod
from domain.entities.zone import Zone
import uuid
from typing import List


class ZoneRepository(ABC):

    @abstractmethod
    def save(self, zone: Zone) -> Zone:
        pass

    @abstractmethod
    def update(self, zone: Zone) -> Zone:
        pass

    @abstractmethod
    def get_by_id(self, zone_id: uuid.UUID) -> Zone | None:
        pass

    @abstractmethod
    def get_all(self) -> List[Zone]:
        pass

    @abstractmethod
    def delete(self, zone_id: uuid.UUID) -> None:
        pass
