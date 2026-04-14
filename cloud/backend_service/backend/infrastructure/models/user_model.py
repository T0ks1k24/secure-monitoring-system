import uuid
from sqlalchemy import Column, DateTime, String, Uuid
from datetime import datetime
from infrastructure.database import Base


class UserModel(Base):

    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
