from typing import Optional
from pydantic import BaseModel, Field

class CameraParams(BaseModel):
    """Common parameters for cameras and global configuration."""
    fps: Optional[float] = Field(
        default=None,
        ge=0.1,
        le=30.0,
        description="Frames per second. Recommended: 1.0-5.0 for detection"
    )
    resize_width: Optional[int] = Field(
        default=None,
        ge=0,
        description="Frame width (px). Recommended: 1280 for quality/speed balance"
    )
    jpeg_quality: Optional[int] = Field(None, ge=1, le=100)
    reconnect_delay: Optional[int] = Field(None, ge=1)

    # Motion detection parameters
    motion_min_contour_area: Optional[int] = Field(None, ge=0)
    motion_threshold: Optional[int] = Field(None, ge=0, le=255)

    # Post-processing parameters
    motion_blur_size: Optional[int] = Field(None, ge=1)
    motion_frames_to_average: Optional[int] = Field(None, ge=1)
    motion_min_duration: Optional[float] = Field(None, ge=0.0)
