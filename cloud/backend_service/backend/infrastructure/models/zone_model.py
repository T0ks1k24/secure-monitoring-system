from sqlalchemy import Column, Integer, String, JSON, Float, Boolean
from infrastructure.database import Base


class ZoneModel(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    camera_id = Column(String, nullable=False, index=True)

    polygon = Column(JSON, nullable=False)

    zone_type = Column(String, nullable=False)
    risk_weight = Column(Float, default=30.0)
    is_active = Column(Boolean, default=True)

    max_people_allowed = Column(Integer, nullable=False)
