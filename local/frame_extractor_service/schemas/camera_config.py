from pydantic import Field
from .motion_config import MotionConfig
from .camera_params import CameraParams

class CameraConfig(CameraParams):
    """Complete camera configuration stored in database."""
    id: int | None = Field(default=None, description="Unique camera ID")
    rtsp: str = Field(..., description="RTSP stream URL")
    name: str | None = Field(default=None, description="Human readable name")
    enabled: bool = Field(default=True, description="Whether camera is active")
    motion: MotionConfig = Field(default_factory=MotionConfig)
