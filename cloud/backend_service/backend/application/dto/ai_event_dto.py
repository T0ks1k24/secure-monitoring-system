from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class BoundingBoxDTO(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class AIEventDTO(BaseModel):
    event_id: str
    camera_id: str
    timestamp: float
    event_type: str
    risk_level: str
    track_id: int | None = None
    object_class: str | None = None
    confidence: float | None = None
    bbox: BoundingBoxDTO | None = None
    zone_id: str | None = None
    zone_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def timestamp_as_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc)
