import uuid
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from infrastructure.database import Base


class EventModel(Base):

    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id = Column(String, nullable=False)
    persons = Column(Integer, nullable=False)
    zone_id = Column(UUID(as_uuid=True), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    risk = Column(String, nullable=False)
