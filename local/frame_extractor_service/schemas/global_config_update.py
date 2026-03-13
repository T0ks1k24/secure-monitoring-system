from typing import Optional

from pydantic import BaseModel, Field

class GlobalConfigUpdate(BaseModel):
    """
    Global settings. Applied as default for new cameras.

    Exception: `ai_service_url` applies to **all** workers at once.
    """

    ai_service_url: Optional[str] = Field(default=None, examples=["http://192.168.1.200:5000/api/v1/detect"])
    default_fps: Optional[float] = Field(default=None, ge=0.1, le=30)
    default_resize_width: Optional[int] = Field(default=None, ge=0)
    default_jpeg_quality: Optional[int] = Field(default=None, ge=1, le=100)
    default_reconnect_delay: Optional[int] = Field(default=None, ge=1)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"summary": "Змінити AI сервіс", "value": {"ai_service_url": "http://192.168.1.200:5000/api/v1/detect"}},
                {"summary": "Знизити навантаження", "value": {"default_fps": 1.0, "default_resize_width": 640, "default_jpeg_quality": 75}},
            ]
        }
    }
