from datetime import datetime
from typing import Any

from domain.enums.risk_enum import RiskLevel


class SecurityEvent:

    def __init__(
        self,
        id: str,
        camera_id: str,
        event_type: str,
        timestamp: datetime,
        risk: RiskLevel,
        object_class: str | None = None,
        track_id: int | None = None,
        confidence: float | None = None,
        zone_id: str | None = None,
        zone_name: str | None = None,
        bbox: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.camera_id = camera_id
        self.id = id
        self.event_type = event_type
        self.timestamp = timestamp
        self.risk = risk
        self.object_class = object_class
        self.track_id = track_id
        self.confidence = confidence
        self.zone_id = zone_id
        self.zone_name = zone_name
        self.bbox = bbox
        self.metadata = metadata or {}
