from typing import Optional

from pydantic import BaseModel, Field, model_validator

from .compat import fold_legacy_motion_fields

class CameraParams(BaseModel):
    """Top-level camera parameters shared by camera request/response models."""
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

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_motion_fields(cls, data):
        return fold_legacy_motion_fields(data)
