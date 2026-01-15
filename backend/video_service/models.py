from pydantic import BaseModel
from typing import List
from datetime import datetime


class BoundingBox(BaseModel):
    x: int
    y: int
    w: int
    h: int


class DetectionResult(BaseModel):
    label: str
    bbox: BoundingBox
    confidence: float


class FrameDetections(BaseModel):
    timestamp: datetime
    camera_id: int
    detections: List[DetectionResult]
