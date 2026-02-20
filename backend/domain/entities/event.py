import uuid
from datetime import datetime
from domain.enums.risk_enum import RiskLevel


class SecurityEvent:

    def __init__(
        self,
        camera_id: str,
        persons: int,
        zone_id: uuid.UUID,
        timestamp: datetime,
        risk: RiskLevel,
        id: uuid.UUID | None = None
    ):

        self.id = id or uuid.uuid4()
        self.camera_id = camera_id
        self.persons = persons
        self.zone_id = zone_id
        self.timestamp = timestamp
        self.risk = risk
