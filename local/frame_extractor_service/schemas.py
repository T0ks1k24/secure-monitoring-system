from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class CameraStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    CONNECTING = "connecting"
    ERROR = "error"


class MotionConfigSchema(BaseModel):
    enabled: bool = Field(
        default=True,
        description="Вмикає/вимикає motion detection. False = надсилати завжди.",
    )
    # ── Фільтр розміру ─────────────────────────────────────────────
    min_contour_area: int = Field(
        default=4000,
        ge=100,
        description=(
            "Мін. площа одного об'єкта (px²). "
            "Листя/вітер дають < 500, людина ~3000–15000, авто ~10000+. "
            "Збільшити якщо багато хибних спрацювань від дерев."
        ),
    )
    min_total_area: int = Field(
        default=6000,
        ge=100,
        description=(
            "Мін. сумарна площа всіх об'єктів (px²). "
            "Захист від шелесту листя — багато дрібних contours разом."
        ),
    )
    # ── Фільтр форми ───────────────────────────────────────────────
    min_solidity: float = Field(
        default=0.4,
        ge=0.1,
        le=1.0,
        description=(
            "Мін. 'щільність' форми (area / convex_hull_area). "
            "Листя: 0.3–0.5. Люди/авто: 0.6–0.95. "
            "Збільшити для фільтрації хаотичних форм."
        ),
    )
    # ── Фільтр стабільності ────────────────────────────────────────
    min_consecutive_frames: int = Field(
        default=2,
        ge=1,
        le=10,
        description=(
            "Скільки кадрів підряд має бути рух для підтвердження. "
            "1 = реагує миттєво, 3+ = фільтрує короткі пориви вітру."
        ),
    )
    # ── Cooldown ───────────────────────────────────────────────────
    cooldown_seconds: float = Field(
        default=10.0,
        ge=0.0,
        description="Секунди після зупинки руху — продовжувати надсилати кадри.",
    )
    # ── Параметри обробки зображення ──────────────────────────────
    blur_size: int = Field(
        default=21,
        ge=3,
        description="Розмір Gaussian blur (непарне число). Більше = менше шуму камери.",
    )
    diff_threshold: int = Field(
        default=25,
        ge=1,
        le=255,
        description="Поріг бінаризації різниці кадрів. Менше = чутливіше до освітлення.",
    )
    dilate_iterations: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Кількість ітерацій dilate. Більше = краще з'єднує частини об'єкта.",
    )


class CameraConfig(BaseModel):
    id: str
    rtsp: str
    name: Optional[str] = None
    fps: Optional[float] = None
    resize_width: Optional[int] = None
    jpeg_quality: Optional[int] = None
    enabled: bool = True
    motion: MotionConfigSchema = Field(default_factory=MotionConfigSchema)


class CameraCreateRequest(BaseModel):
    id: str
    rtsp: str
    name: Optional[str] = None
    fps: Optional[float] = Field(default=None, ge=0.1, le=30)
    resize_width: Optional[int] = Field(default=None, ge=0)
    jpeg_quality: Optional[int] = Field(default=None, ge=1, le=100)
    enabled: bool = True
    motion: MotionConfigSchema = Field(default_factory=MotionConfigSchema)


class CameraUpdateRequest(BaseModel):
    rtsp: Optional[str] = None
    name: Optional[str] = None
    fps: Optional[float] = Field(default=None, ge=0.1, le=30)
    resize_width: Optional[int] = Field(default=None, ge=0)
    jpeg_quality: Optional[int] = Field(default=None, ge=1, le=100)
    motion: Optional[MotionConfigSchema] = None


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
    frames_skipped: int
    motion_events: int
    motion_active: bool
    enabled: bool
    motion: MotionConfigSchema


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
