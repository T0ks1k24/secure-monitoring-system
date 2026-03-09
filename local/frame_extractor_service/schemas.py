from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class CameraStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    CONNECTING = "connecting"
    ERROR = "error"


class CameraConfig(BaseModel):
    id: str
    rtsp: str
    name: Optional[str] = None
    fps: Optional[float] = None
    resize_width: Optional[int] = None
    jpeg_quality: Optional[int] = None
    enabled: bool = True


class CameraCreateRequest(BaseModel):
    id: str
    rtsp: str
    name: Optional[str] = None
    fps: Optional[float] = Field(default=None, ge=0.1, le=30)
    resize_width: Optional[int] = Field(default=None, ge=0)
    jpeg_quality: Optional[int] = Field(default=None, ge=1, le=100)
    enabled: bool = True


class CameraUpdateRequest(BaseModel):
    rtsp: Optional[str] = None
    name: Optional[str] = None
    fps: Optional[float] = Field(default=None, ge=0.1, le=30)
    resize_width: Optional[int] = Field(default=None, ge=0)
    jpeg_quality: Optional[int] = Field(default=None, ge=1, le=100)


class CameraStatusResponse(BaseModel):
    id: str
    name: Optional[str]
    rtsp: str
    status: CameraStatus
    fps: float
    resize_width: int
    jpeg_quality: int
    frames_sent: int
    frames_failed: int
    enabled: bool


class GlobalConfigUpdate(BaseModel):
    ai_service_url: Optional[str] = None
    default_fps: Optional[float] = Field(default=None, ge=0.1, le=30)
    default_resize_width: Optional[int] = Field(default=None, ge=0)
    default_jpeg_quality: Optional[int] = Field(default=None, ge=1, le=100)
    default_reconnect_delay: Optional[int] = Field(default=None, ge=1)


class ServiceStatusResponse(BaseModel):
    running: bool
    total_cameras: int
    active_cameras: int
    ai_service_url: str
    global_fps: float
    global_resize_width: int
    global_jpeg_quality: int
