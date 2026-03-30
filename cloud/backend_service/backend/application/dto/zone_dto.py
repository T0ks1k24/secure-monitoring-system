from pydantic import BaseModel, ConfigDict
from typing import List


class ZoneBaseDTO(BaseModel):
    name: str
    camera_id: str
    polygon: List[List[float]]
    zone_type: str
    risk_weight: float
    is_active: bool
    max_people_allowed: int

    model_config = ConfigDict(from_attributes=True)


class ZoneCreateDTO(ZoneBaseDTO):
    pass


class ZoneUpdateDTO(BaseModel):
    name: str | None = None
    camera_id: str | None = None
    polygon: List[List[float]] | None = None
    zone_type: str | None = None
    risk_weight: float | None = None
    is_active: bool | None = None
    max_people_allowed: int | None = None


class ZoneResponseDTO(ZoneBaseDTO):
    id: int
