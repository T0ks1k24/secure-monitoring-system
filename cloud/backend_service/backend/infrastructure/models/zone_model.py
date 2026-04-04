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
    time_windows = Column(JSON, nullable=False, default=list)
    base_mode = Column(String, nullable=False, default="STRICT")
    risk_multipliers = Column(
        JSON,
        nullable=False,
        default=lambda: {"relaxed": 0.3, "strict": 1.5},
    )
    people_thresholds = Column(
        JSON,
        nullable=False,
        default=lambda: {"medium": 2, "high": 5},
    )
    accumulation = Column(
        JSON,
        nullable=False,
        default=lambda: {"decay_per_second": 1.0},
    )
    cooldown_seconds = Column(Float, nullable=False, default=5.0)
