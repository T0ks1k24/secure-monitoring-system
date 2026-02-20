from pydantic import BaseModel
from uuid import UUID
from typing import List


class ZoneCreateDTO(BaseModel):

    name: str
    coordinates: List[List[int]]
    max_people_allowed: int


class ZoneUpdateDTO(BaseModel):

    name: str | None = None
    coordinates: List[List[int]] | None = None
    max_people_allowed: int | None = None


class ZoneResponseDTO(BaseModel):

    id: UUID
    name: str
    coordinates: List[List[int]]
    max_people_allowed: int
