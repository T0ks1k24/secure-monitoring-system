from typing import Optional
from pydantic import BaseModel, Field
from .motion_config import MotionConfig

class CameraConfig(BaseModel):
    id: str = Field(..., description="Unique camera ID")
    rtsp: str = Field(..., description="RTSP stream URL")
    name: Optional[str] = Field(default=None, description="Human readable name")
    enabled: bool = Field(default=True, description="Whether camera is active")
    fps: Optional[float] = Field(default=None, ge=0.1, le=30)
    resize_width: Optional[int] = Field(default=None, ge=0)
    jpeg_quality: Optional[int] = Field(default=None, ge=1, le=100)
    motion: MotionConfig = Field(default_factory=MotionConfig)
