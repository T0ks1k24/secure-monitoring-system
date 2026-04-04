from typing import List

from pydantic import BaseModel, ConfigDict, Field


class TimeWindowDTO(BaseModel):
    start: str = Field(
        ...,
        description="Початок relax-вікна у форматі HH:MM (локальний час об'єкта).",
        examples=["09:00"],
    )
    end: str = Field(
        ...,
        description="Кінець relax-вікна у форматі HH:MM. Поза вікном зона працює в STRICT.",
        examples=["10:00"],
    )


class RiskMultipliersDTO(BaseModel):
    relaxed: float = Field(
        default=0.3,
        description="Множник приросту risk_score в RELAXED режимі.",
        examples=[0.3],
    )
    strict: float = Field(
        default=1.5,
        description="Множник приросту risk_score в STRICT режимі.",
        examples=[1.5],
    )


class PeopleThresholdsDTO(BaseModel):
    medium: int = Field(
        default=2,
        description="Поріг кількості людей для рівня MEDIUM у RELAXED режимі.",
        examples=[2],
    )
    high: int = Field(
        default=5,
        description="Поріг кількості людей для рівня HIGH у RELAXED режимі.",
        examples=[5],
    )


class AccumulationDTO(BaseModel):
    decay_per_second: float = Field(
        default=1.0,
        description="Швидкість спадання risk_score за секунду, коли в зоні немає людей.",
        examples=[1.0],
    )


class ZoneBaseDTO(BaseModel):
    name: str = Field(..., description="Людинозрозуміла назва зони.", examples=["Warehouse A"])
    camera_id: str = Field(..., description="ID камери, до якої належить зона.", examples=["1"])
    polygon: List[List[float]] = Field(
        ...,
        description="Полігон зони у нормалізованих координатах [x,y] (0..1). Мінімум 3 точки.",
        examples=[[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]],
    )
    zone_type: str = Field(..., description="Тип зони (restricted/perimeter/parking тощо).")
    risk_weight: float = Field(
        ...,
        description="Загальна вага ризику для legacy-правил. Використовується існуючою логікою сумісності.",
        examples=[30.0],
    )
    is_active: bool = Field(
        ...,
        description="Чи активна зона для аналітики. Неактивні зони ігноруються.",
        examples=[True],
    )
    max_people_allowed: int = Field(
        ...,
        description="Ліміт людей для legacy crowding-правил.",
        examples=[3],
    )
    time_windows: List[TimeWindowDTO] = Field(
        default_factory=list,
        description="Список RELAXED інтервалів. Якщо поточний час у будь-якому інтервалі, mode=RELAXED.",
    )
    base_mode: str = Field(
        default="STRICT",
        description="Базовий режим зони поза time_windows. Рекомендовано STRICT.",
        examples=["STRICT"],
    )
    risk_multipliers: RiskMultipliersDTO = Field(
        default_factory=RiskMultipliersDTO,
        description="Множники для накопичення risk_score по режимах.",
    )
    people_thresholds: PeopleThresholdsDTO = Field(
        default_factory=PeopleThresholdsDTO,
        description="Пороги людей для інтерпретації crowd-ризику у RELAXED режимі.",
    )
    accumulation: AccumulationDTO = Field(
        default_factory=AccumulationDTO,
        description="Налаштування накопичення/затухання risk_score.",
    )
    cooldown_seconds: float = Field(
        default=5.0,
        description="Мінімальна пауза між подіями з цієї зони (anti-spam).",
        examples=[5.0],
    )

    model_config = ConfigDict(from_attributes=True)


class ZoneCreateDTO(ZoneBaseDTO):
    pass


class ZoneUpdateDTO(BaseModel):
    name: str | None = Field(default=None, description="Нова назва зони.")
    camera_id: str | None = Field(default=None, description="Новий ID камери для зони.")
    polygon: List[List[float]] | None = Field(
        default=None,
        description="Новий полігон зони у нормалізованих координатах.",
    )
    zone_type: str | None = Field(default=None, description="Новий тип зони.")
    risk_weight: float | None = Field(default=None, description="Нова legacy-вага ризику.")
    is_active: bool | None = Field(default=None, description="Активувати/деактивувати зону.")
    max_people_allowed: int | None = Field(default=None, description="Новий legacy-ліміт людей.")
    time_windows: List[TimeWindowDTO] | None = Field(
        default=None,
        description="Повний новий список RELAXED інтервалів.",
    )
    base_mode: str | None = Field(default=None, description="Базовий режим поза вікнами часу.")
    risk_multipliers: RiskMultipliersDTO | None = Field(
        default=None,
        description="Нові множники накопичення risk_score.",
    )
    people_thresholds: PeopleThresholdsDTO | None = Field(
        default=None,
        description="Нові пороги людей для RELAXED правил.",
    )
    accumulation: AccumulationDTO | None = Field(
        default=None,
        description="Нові параметри decay/accumulation.",
    )
    cooldown_seconds: float | None = Field(
        default=None,
        description="Новий anti-spam cooldown у секундах.",
    )


class ZoneResponseDTO(ZoneBaseDTO):
    id: int
