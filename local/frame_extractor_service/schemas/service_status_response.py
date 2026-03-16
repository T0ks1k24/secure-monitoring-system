from pydantic import BaseModel, Field


class ServiceStatusResponse(BaseModel):
    running: bool
    total_cameras: int  = Field(description="Total cameras in config")
    active_cameras: int = Field(description="Cameras with status running")
    ai_service_url: str
    fps: float
    resize_width: int
    jpeg_quality: int
