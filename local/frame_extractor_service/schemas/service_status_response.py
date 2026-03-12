from pydantic import BaseModel, Field


class ServiceStatusResponse(BaseModel):
    running: bool
    total_cameras: int  = Field(description="Всього камер у конфіг")
    active_cameras: int = Field(description="Зі статусом running")
    ai_service_url: str
    global_fps: float
    global_resize_width: int
    global_jpeg_quality: int
