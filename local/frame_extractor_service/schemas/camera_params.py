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
    jpeg_quality: Optional[int] = Field(
        default=None, 
        ge=1, 
        le=100, 
        description="JPEG compression quality (1-100). Recommended: 85"
    )
