from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class BoundingBoxDTO(BaseModel):
    x1: float = Field(..., description="Ліва X-координата bbox у нормалізованих координатах (0..1).")
    y1: float = Field(..., description="Верхня Y-координата bbox у нормалізованих координатах (0..1).")
    x2: float = Field(..., description="Права X-координата bbox у нормалізованих координатах (0..1).")
    y2: float = Field(..., description="Нижня Y-координата bbox у нормалізованих координатах (0..1).")


class AIEventDTO(BaseModel):
    event_id: str = Field(..., description="Унікальний ID події, згенерований AI сервісом.")
    camera_id: str = Field(..., description="ID камери, з якої надійшла подія.")
    timestamp: float = Field(..., description="Unix timestamp події (UTC, секунди).")
    event_type: str = Field(..., description="Тип події (наприклад zone_intrusion, weapon_detected).")
    risk_level: str = Field(..., description="Рівень ризику події: low|medium|high|critical.")
    track_id: int | None = Field(default=None, description="ID треку об'єкта, якщо подія прив'язана до треку.")
    object_class: str | None = Field(default=None, description="Клас об'єкта (person, car, knife тощо).")
    confidence: float | None = Field(default=None, description="Довіра моделі до класифікації об'єкта (0..1).")
    bbox: BoundingBoxDTO | None = Field(default=None, description="Bounding box об'єкта, якщо доступний.")
    zone_id: str | None = Field(default=None, description="ID зони, якщо подія зонова.")
    zone_name: str | None = Field(default=None, description="Назва зони для швидкого відображення у UI.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Додаткові поля події: mode, people_count, risk_score, evidence_url тощо.",
    )

    def timestamp_as_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc)
