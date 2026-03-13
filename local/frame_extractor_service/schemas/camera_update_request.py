from typing import Optional

from pydantic import BaseModel, Field

from .motion_config import MotionConfig

class CameraUpdateRequest(BaseModel):
    """
    Update camera. All fields are optional.

    ```json
    { "fps": 5.0 }
    { "motion": { "min_contour_area": ​​8000 } }
    ```
    """

    rtsp: Optional[str] = Field(default=None, description="Новий RTSP URL.")
    name: Optional[str] = Field(default=None)
    fps: Optional[float] = Field(default=None, ge=0.1, le=30)
    resize_width: Optional[int] = Field(default=None, ge=0)
    jpeg_quality: Optional[int] = Field(default=None, ge=1, le=100)
    motion: Optional[MotionConfig] = Field(default=None, description="Замінює весь об'єкт motion.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"summary": "Змінити FPS", "value": {"fps": 5.0}},
                {"summary": "Налаштувати motion", "value": {"motion": {"min_contour_area": 8000, "cooldown_seconds": 5.0}}},
                {"summary": "Новий URL + якість", "value": {"rtsp": "rtsp://192.168.1.100:554/stream2", "jpeg_quality": 95}},
            ]
        }
    }
