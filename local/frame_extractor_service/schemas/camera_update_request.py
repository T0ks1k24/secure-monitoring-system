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
    rtsp: str | None = None
    name: str | None = None
    motion: MotionUpdateRequest | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"summary": "Change FPS", "value": {"fps": 5.0}},
                {"summary": "Setup motion", "value": {"motion": {"min_contour_area": 8000, "cooldown_seconds": 5.0}}},
                {"summary": "New URL + quality", "value": {"rtsp": "rtsp://192.168.1.100:554/stream2", "jpeg_quality": 95}},
            ]
        }
    }
