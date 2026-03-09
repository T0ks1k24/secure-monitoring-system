import uuid
from datetime import datetime
from domain.enums.role_enum import UserRole


class User:

    def __init__(
        self,
        username: str,
        password_hash: str,
        role: UserRole,
        id: uuid.UUID | None = None,
        created_at: datetime | None = None
    ):

        self.id = id or uuid.uuid4()
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.created_at = created_at or datetime.utcnow()
