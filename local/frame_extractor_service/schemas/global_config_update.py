from .camera_params import CameraParams
from pydantic import Field

class GlobalConfigUpdate(CameraParams):
    """
    Global settings. Applied as default for new cameras.

    Exception: `ai_service_url` applies to **all** workers at once.
    """
    ai_service_url: str | None = Field(default=None, examples=["http://192.168.1.200:5000/api/v1/detect"])
    default_reconnect_delay: int | None = Field(default=None, ge=1)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"summary": "Change AI service", "value": {"ai_service_url": "http://192.168.1.200:5000/api/v1/detect"}},
                {"summary": "Reduce load", "value": {"fps": 1.0, "resize_width": 640, "jpeg_quality": 75}},
            ]
        }
    }
