from typing import Optional

from pydantic import BaseModel, Field

from .camera_status import CameraStatus
from .motion_config import MotionConfig

class CameraStatusResponse(BaseModel):
    """Full camera status with current statistics."""
    id: int
    name: Optional[str]
    rtsp: str
    status: CameraStatus
    fps: float
    resize_width: int
    jpeg_quality: int
    frames_sent: int    = Field(description="Frames sent to AI")
    frames_failed: int  = Field(description="Frames failed to send")
    frames_skipped: int = Field(description="Frames skipped — no motion")
    motion_events: int  = Field(description="Confirmed motion events")
    motion_active: bool = Field(description="Motion is currently active")
    enabled: bool
    motion: MotionConfig
