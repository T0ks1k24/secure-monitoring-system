"""
Схеми подій та зон для AI сервісу.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


# ── Risk levels ───────────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW      = "low"       # Нормальна активність
    MEDIUM   = "medium"    # Варто звернути увагу
    HIGH     = "high"      # Потрібна реакція
    CRITICAL = "critical"  # Негайна реакція


# ── Event types ───────────────────────────────────────────────────────────────

class EventType(str, Enum):
    # Об'єктні події
    PERSON_DETECTED       = "person_detected"
    VEHICLE_DETECTED      = "vehicle_detected"
    WEAPON_DETECTED       = "weapon_detected"
    ANIMAL_DETECTED       = "animal_detected"
    UNKNOWN_OBJECT        = "unknown_object"

    # Зонові події
    ZONE_INTRUSION        = "zone_intrusion"       # Об'єкт увійшов у заборонену зону
    ZONE_LOITERING        = "zone_loitering"       # Об'єкт довго в зоні
    ZONE_CROWDING         = "zone_crowding"        # Забагато об'єктів у зоні

    # Поведінкові події (траєкторія)
    RUNNING_DETECTED      = "running_detected"     # Швидкий рух
    DIRECTION_VIOLATION   = "direction_violation"  # Рух проти дозволеного напряму
    ABANDONED_OBJECT      = "abandoned_object"     # Об'єкт залишений без руху

    # Системні
    CAMERA_OFFLINE        = "camera_offline"


# ── Zone schemas ──────────────────────────────────────────────────────────────

class ZoneType(str, Enum):
    RESTRICTED      = "restricted"       # Заборонена зона — будь-хто = HIGH
    ENTRANCE        = "entrance"         # Зона входу — контроль напряму
    PARKING         = "parking"          # Парковка — тільки авто OK
    PEDESTRIAN      = "pedestrian"       # Пішохідна — авто = HIGH
    PERIMETER       = "perimeter"        # Периметр — будь-який рух вночі = HIGH
    COUNTING_LINE   = "counting_line"    # Лінія підрахунку перетинів
    SAFE_ZONE       = "safe_zone"        # Безпечна зона — ризик знижується


class ZoneRule(BaseModel):
    """Правило ризику для конкретного типу об'єкта в зоні."""
    object_class: str                          # "person", "car", "knife", "*" = будь-який
    risk_level: RiskLevel
    event_type: EventType
    # Затримка спрацювання (секунди в зоні до генерації події)
    trigger_after_seconds: float = 0.0
    # Максимум об'єктів цього класу без тривоги (для crowding)
    max_count: Optional[int] = None
    # Тільки в певний час (HH:MM–HH:MM), None = завжди
    active_time_start: Optional[str] = None
    active_time_end: Optional[str] = None


class RiskSchedule(BaseModel):
    """
    Вікно зниження ризику — коли приходять робітники/персонал.

    Приклад:
      {"time_start": "08:00", "time_end": "17:00",
       "reduce_by": 2, "days": [0,1,2,3,4]}
      → В будні з 8 до 17 ризик знижується на 2 рівні:
        CRITICAL→MEDIUM, HIGH→LOW, MEDIUM→LOW, LOW→LOW

    reduce_by:
      1 = знизити на один рівень (HIGH → MEDIUM)
      2 = знизити на два рівні  (HIGH → LOW)
      3 = повне придушення      (будь-який → LOW)

    Важливо: WEAPON_DETECTED ніколи не знижується незалежно від розкладу.

    days: список днів тижня (0=пн, 1=вт, ..., 6=нд). None = кожен день.

    timezone: назва timezone (напр. "Europe/Kiev"). None = UTC.
    """
    time_start: str   # "HH:MM"
    time_end: str     # "HH:MM"  (може бути менше time_start → перетин північ)
    reduce_by: int = Field(default=1, ge=1, le=3)
    days: Optional[List[int]] = None   # None = щодня
    timezone: Optional[str] = None
    label: Optional[str] = None        # Описова назва ("Робочі години", "Змiна А")


class Zone(BaseModel):
    """Зона аналітики — полігон на кадрі камери."""
    id: str
    camera_id: str
    name: str
    zone_type: ZoneType
    # Полігон у нормалізованих координатах (0.0–1.0)
    # [[x1,y1], [x2,y2], ...] — мінімум 3 точки
    polygon: List[List[float]]
    rules: List[ZoneRule] = Field(default_factory=list)
    # Дозволений напрям руху (градуси, None = будь-який)
    allowed_direction: Optional[float] = None
    allowed_direction_tolerance: float = 45.0
    # Максимальний час перебування (секунди) до loitering-події
    max_dwell_seconds: Optional[float] = None
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # Розклади зниження ризику (довільна кількість непересічних вікон)
    risk_schedules: List[RiskSchedule] = Field(default_factory=list)


# ── Detection schemas ─────────────────────────────────────────────────────────

class BoundingBox(BaseModel):
    """Bounding box у нормалізованих координатах (0.0–1.0)."""
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_pixels(self, frame_w: int, frame_h: int) -> "BoundingBox":
        return BoundingBox(
            x1=self.x1 * frame_w, y1=self.y1 * frame_h,
            x2=self.x2 * frame_w, y2=self.y2 * frame_h,
        )


class TrackedObject(BaseModel):
    """Детекція з ID треку та аналітикою траєкторії."""
    track_id: int
    object_class: str
    confidence: float
    bbox: BoundingBox

    # Траєкторія (список центроїдів за останні N кадрів)
    trajectory: List[List[float]] = Field(default_factory=list)
    # Швидкість (px/frame у нормалізованих координатах)
    speed: float = 0.0
    # Напрям руху (градуси, 0=вгору, 90=вправо, 180=вниз, 270=вліво)
    direction: Optional[float] = None
    # Скільки кадрів трек активний
    age_frames: int = 0
    # Скільки секунд перебуває в кожній зоні {zone_id: seconds}
    dwell_time: Dict[str, float] = Field(default_factory=dict)


# ── Security event (те що публікується в RabbitMQ) ───────────────────────────

class SecurityEvent(BaseModel):
    event_id: str
    camera_id: str
    timestamp: float                    # Unix timestamp

    event_type: EventType
    risk_level: RiskLevel

    # Об'єкт що спричинив подію
    track_id: Optional[int] = None
    object_class: Optional[str] = None
    confidence: Optional[float] = None
    bbox: Optional[BoundingBox] = None

    # Зона (якщо подія зонова)
    zone_id: Optional[str] = None
    zone_name: Optional[str] = None

    # Додаткові дані (швидкість, кількість об'єктів тощо)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # RabbitMQ routing key: "events.{event_type}.{camera_id}"
    @property
    def routing_key(self) -> str:
        # .value needed for Python 3.11+ where str(StrEnum) = "ClassName.member"
        return f"events.{self.event_type.value}.{self.camera_id}"


# ── API schemas ───────────────────────────────────────────────────────────────

class DetectRequest(BaseModel):
    camera_id: str
    # Timestamp кадру (Unix). None = поточний час
    frame_timestamp: Optional[float] = None
    # fps потоку — для розрахунку часу в зонах
    stream_fps: float = 10.0


class DetectResponse(BaseModel):
    camera_id: str
    frame_timestamp: float
    tracked_objects: List[TrackedObject]
    events_published: int
    processing_time_ms: float


class ZoneUpdateMessage(BaseModel):
    """Повідомлення від Backend коли зони оновлюються."""
    camera_id: str
    action: str   # "reload" | "clear"


class ServiceStatus(BaseModel):
    running: bool
    model_loaded: bool
    model_path: str
    device: str
    active_trackers: int          # кількість камер з активними треками
    total_zones_cached: int
    rabbitmq_connected: bool
    uptime_seconds: float
