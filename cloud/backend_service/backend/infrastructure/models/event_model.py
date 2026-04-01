from sqlalchemy import Column, DateTime, Float, Integer, JSON, String
from infrastructure.database import Base


class EventModel(Base):

    __tablename__ = "events"

    id = Column(String, primary_key=True)
    camera_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    object_class = Column(String, nullable=True)
    track_id = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    zone_id = Column(String, nullable=True)
    zone_name = Column(String, nullable=True)
    risk = Column(String, nullable=False)
    bbox = Column(JSON, nullable=True)
    event_metadata = Column("metadata", JSON, nullable=False, default=dict)
