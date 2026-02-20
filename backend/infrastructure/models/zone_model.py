import uuid
from sqlalchemy import Column, String, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from infrastructure.database import Base


class ZoneModel(Base):

    __tablename__ = "zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    coordinates = Column(JSON, nullable=False)
    max_people_allowed = Column(Integer, nullable=False)
