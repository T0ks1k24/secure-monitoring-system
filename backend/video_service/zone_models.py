from pydantic import BaseModel
from typing import List


class Zone(BaseModel):
    id: int
    camera_id: int
    name: str
    polygon: List[List[int]]  # [[x,y], [x,y], ...]
    forbidden_classes: List[str]
