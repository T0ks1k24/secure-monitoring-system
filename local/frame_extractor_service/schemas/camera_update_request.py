from typing import Optional
from pydantic import Field
from .motion_config import MotionUpdateRequest
from .camera_params import CameraParams

class CameraUpdateRequest(CameraParams):
    """
    Update camera. All fields are optional.

    ```json
    { "fps": 5.0 }
    { "motion": { "min_contour_area": 8000 } }
    ```
    """
    ai_service_url: str | None = Field(
        default=None,
        examples=["http://192.168.1.200:5000/api/v1/detect"],
        description="The URL of the AI service to which the frames will be sent for processing."
    )
    default_reconnect_delay: int | None = Field(default=None, ge=1)
    rtsp: str | None = None
    enabled: Optional[bool] = Field(None, description="Enable or disable the camera processing.")
    name: str | None = None
    motion: MotionUpdateRequest | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"summary": "Change FPS", "value": {"fps": 5.0}},
                {"summary": "Setup motion", "value": {"motion": {"min_contour_area": 8000, "cooldown_seconds": 5.0}}},
                {
                    "summary": "New URL + quality",
                    "value": {"rtsp": "rtsp://192.168.1.100:554/stream2", "jpeg_quality": 95}
                },
            ]
        }
    }
