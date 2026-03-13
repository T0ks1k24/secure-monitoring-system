from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class AIEventDTO(BaseModel):

    camera_id: str
    persons_detected: int
    zone_id: UUID
    timestamp: datetime
