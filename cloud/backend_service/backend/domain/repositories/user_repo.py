from abc import ABC, abstractmethod
from domain.entities.user import User
import uuid


class UserRepository(ABC):

    @abstractmethod
    def save(self, user: User) -> User:
        pass

    @abstractmethod
    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> User | None:
        pass

    @abstractmethod
    def delete(self, user_id: uuid.UUID) -> None:
        pass

    @abstractmethod
    def get_all(self):
        pass
