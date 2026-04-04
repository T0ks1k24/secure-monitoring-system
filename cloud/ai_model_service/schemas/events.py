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
    ZONE_SMART_ACTIVITY   = "zone_smart_activity"  # Смарт-аналітика присутності людей

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
    object_class: str = Field(
        ...,
        description='Клас обʼєкта: "person", "car", "knife" або "*" для будь-якого.',
    )
    risk_level: RiskLevel = Field(..., description="Базовий рівень ризику для цього правила.")
    event_type: EventType = Field(..., description="Тип події, яку створює це правило.")
    # Затримка спрацювання (секунди в зоні до генерації події)
    trigger_after_seconds: float = Field(
        default=0.0,
        description="Скільки секунд обʼєкт має бути в зоні до спрацювання правила.",
    )
    # Максимум об'єктів цього класу без тривоги (для crowding)
    max_count: Optional[int] = Field(
        default=None,
        description="Максимальна кількість об'єктів цього класу без тривоги.",
    )
    # Тільки в певний час (HH:MM–HH:MM), None = завжди
    active_time_start: Optional[str] = Field(
        default=None,
        description="Початок часової дії правила у форматі HH:MM.",
    )
    active_time_end: Optional[str] = Field(
        default=None,
        description="Кінець часової дії правила у форматі HH:MM.",
    )


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
    time_start: str = Field(..., description='Початок вікна розкладу, формат "HH:MM".')
    time_end: str = Field(
        ...,
        description='Кінець вікна розкладу, формат "HH:MM" (може перетинати північ).',
    )
    reduce_by: int = Field(default=1, ge=1, le=3)
    days: Optional[List[int]] = Field(
        default=None,
        description="Дні тижня: 0=понеділок ... 6=неділя. None означає щодня.",
    )
    timezone: Optional[str] = Field(
        default=None,
        description='Назва timezone (наприклад "Europe/Kyiv"). None = локальний час сервісу.',
    )
    label: Optional[str] = Field(default=None, description="Людинозрозуміла назва розкладу.")


class Zone(BaseModel):
    """Зона аналітики — полігон на кадрі камери."""
    id: str = Field(..., description="Унікальний ID зони.")
    camera_id: str = Field(..., description="ID камери, якій належить зона.")
    name: str = Field(..., description="Назва зони для UI та журналу подій.")
    zone_type: ZoneType = Field(..., description="Тип зони.")
    # Полігон у нормалізованих координатах (0.0–1.0)
    # [[x1,y1], [x2,y2], ...] — мінімум 3 точки
    polygon: List[List[float]] = Field(
        ...,
        description="Полігон у нормалізованих координатах [x,y] в діапазоні 0..1.",
    )
    rules: List[ZoneRule] = Field(
        default_factory=list,
        description="Кастомні правила подій для зони. Якщо порожньо, використовуються default правила.",
    )
    # Дозволений напрям руху (градуси, None = будь-який)
    allowed_direction: Optional[float] = Field(
        default=None,
        description="Дозволений напрямок руху у градусах. None = будь-який напрямок.",
    )
    allowed_direction_tolerance: float = Field(
        default=45.0,
        description="Допустиме відхилення від allowed_direction у градусах.",
    )
    # Максимальний час перебування (секунди) до loitering-події
    max_dwell_seconds: Optional[float] = Field(
        default=None,
        description="Максимальний час перебування в зоні до loitering-події.",
    )
    enabled: bool = Field(default=True, description="Чи активна зона в аналітиці.")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Розширені налаштування з backend (time_windows, multipliers, thresholds, cooldown).",
    )
    # Розклади зниження ризику (довільна кількість непересічних вікон)
    risk_schedules: List[RiskSchedule] = Field(
        default_factory=list,
        description="Розклади, які знижують risk_level для подій у певні часові вікна.",
    )


# ── Detection schemas ─────────────────────────────────────────────────────────

class BoundingBox(BaseModel):
    """Bounding box у нормалізованих координатах (0.0–1.0)."""
    x1: float = Field(..., description="Ліва межа bbox по X.")
    y1: float = Field(..., description="Верхня межа bbox по Y.")
    x2: float = Field(..., description="Права межа bbox по X.")
    y2: float = Field(..., description="Нижня межа bbox по Y.")

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
    track_id: int = Field(..., description="Стабільний ID треку об'єкта в межах камери.")
    object_class: str = Field(..., description="Клас об'єкта (person, car, knife тощо).")
    confidence: float = Field(..., description="Впевненість моделі в класифікації, 0..1.")
    bbox: BoundingBox = Field(..., description="Поточний bounding box об'єкта.")

    # Траєкторія (список центроїдів за останні N кадрів)
    trajectory: List[List[float]] = Field(
        default_factory=list,
        description="Останні центроїди об'єкта для аналізу траєкторії.",
    )
    # Швидкість (px/frame у нормалізованих координатах)
    speed: float = Field(default=0.0, description="Оцінена швидкість руху об'єкта.")
    # Напрям руху (градуси, 0=вгору, 90=вправо, 180=вниз, 270=вліво)
    direction: Optional[float] = Field(default=None, description="Напрямок руху в градусах.")
    # Скільки кадрів трек активний
    age_frames: int = Field(default=0, description="Скільки кадрів трек уже активний.")
    # Скільки секунд перебуває в кожній зоні {zone_id: seconds}
    dwell_time: Dict[str, float] = Field(
        default_factory=dict,
        description="Скільки секунд об'єкт перебуває в кожній зоні: {zone_id: seconds}.",
    )


# ── Security event (те що публікується в RabbitMQ) ───────────────────────────

class SecurityEvent(BaseModel):
    event_id: str = Field(..., description="Унікальний ідентифікатор події.")
    camera_id: str = Field(..., description="ID камери, що згенерувала подію.")
    timestamp: float = Field(..., description="Unix timestamp події (UTC, секунди).")

    event_type: EventType = Field(..., description="Тип події.")
    risk_level: RiskLevel = Field(..., description="Підсумковий рівень ризику події.")

    # Об'єкт що спричинив подію
    track_id: Optional[int] = Field(default=None, description="ID треку, якщо подія об'єктна.")
    object_class: Optional[str] = Field(default=None, description="Клас об'єкта, якщо застосовно.")
    confidence: Optional[float] = Field(default=None, description="Впевненість моделі для об'єктної події.")
    bbox: Optional[BoundingBox] = Field(default=None, description="Координати об'єкта для події.")

    # Зона (якщо подія зонова)
    zone_id: Optional[str] = Field(default=None, description="ID зони, якщо подія зонова.")
    zone_name: Optional[str] = Field(default=None, description="Назва зони, якщо подія зонова.")

    # Додаткові дані (швидкість, кількість об'єктів тощо)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Додаткова аналітика події (mode, people_count, risk_score, evidence_url тощо).",
    )

    # RabbitMQ routing key: "events.{event_type}.{camera_id}"
    @property
    def routing_key(self) -> str:
        # .value needed for Python 3.11+ where str(StrEnum) = "ClassName.member"
        return f"events.{self.event_type.value}.{self.camera_id}"


# ── API schemas ───────────────────────────────────────────────────────────────

class DetectRequest(BaseModel):
    camera_id: str = Field(..., description="ID камери, для якої виконується аналіз кадру.")
    # Timestamp кадру (Unix). None = поточний час
    frame_timestamp: Optional[float] = Field(
        default=None,
        description="Unix timestamp кадру. Якщо не передано, використовується поточний час.",
    )
    # fps потоку — для розрахунку часу в зонах
    stream_fps: float = Field(
        default=10.0,
        description="FPS потоку, використовується для обчислення dwell/trajectory-аналітики.",
    )


class DetectResponse(BaseModel):
    camera_id: str = Field(..., description="ID камери для обробленого кадру.")
    frame_timestamp: float = Field(..., description="Unix timestamp кадру.")
    tracked_objects: List[TrackedObject] = Field(
        ...,
        description="Список об'єктів, які трекер підтвердив на кадрі.",
    )
    events_published: int = Field(
        ...,
        description="Скільки подій було успішно відправлено в RabbitMQ.",
    )
    processing_time_ms: float = Field(..., description="Час обробки кадру в мілісекундах.")


class ZoneUpdateMessage(BaseModel):
    """Повідомлення від Backend коли зони оновлюються."""
    camera_id: str = Field(..., description="ID камери, для якої треба оновити кеш зон.")
    action: str = Field(..., description='Тип дії: "reload" або "clear".')


class ServiceStatus(BaseModel):
    running: bool = Field(..., description="Чи запущений AI сервіс.")
    model_loaded: bool = Field(..., description="Чи завантажена модель детекції.")
    model_path: str = Field(..., description="Шлях до файлу моделі.")
    device: str = Field(..., description="Обчислювальний пристрій (cpu/cuda).")
    active_trackers: int = Field(..., description="Кількість камер з активними трекерами.")
    total_zones_cached: int = Field(..., description="Скільки зон зараз у кеші AI сервісу.")
    rabbitmq_connected: bool = Field(..., description="Статус підключення до RabbitMQ.")
    uptime_seconds: float = Field(..., description="Скільки секунд сервіс працює без рестарту.")
