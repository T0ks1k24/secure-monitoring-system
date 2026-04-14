from pydantic import Field
from .motion_config import MotionConfig
from .camera_params import CameraParams

class CameraAddRequest(CameraParams):
    """Request to add a new camera."""
    rtsp: str = Field(..., description="RTSP stream URL")
    name: str | None = Field(default=None, description="Human readable name")
    enabled: bool = Field(default=True, description="Whether the camera is activated immediately")
    motion: MotionConfig = Field(default_factory=MotionConfig)
