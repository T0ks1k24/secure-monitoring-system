from typing import Optional

from pydantic import BaseModel, Field

from .camera_status import CameraStatus
from .motion_config import MotionConfig

class CameraStatusResponse(BaseModel):
    """Full camera status with current statistics."""
    id: str
    name: Optional[str]
    rtsp: str
    status: CameraStatus
    fps: float
    resize_width: int
    jpeg_quality: int
    frames_sent: int    = Field(description="Кадрів надіслано на AI")
    frames_failed: int  = Field(description="Кадрів не вдалось надіслати")
    frames_skipped: int = Field(description="Кадрів пропущено — немає руху")
    motion_events: int  = Field(description="Підтверджених подій руху")
    motion_active: bool = Field(description="Рух зараз активний")
    enabled: bool
    motion: MotionConfig
