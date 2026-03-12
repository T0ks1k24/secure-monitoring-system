from pydantic import BaseModel, Field


class MotionConfig(BaseModel):
    """
    Motion detector setup based on **background model**.

    The detector compares each frame to the background model (not the previous frame).
    The background is updated slowly when quiet (`background_update_alpha`).

    ### Typical values ​​by scenario

    | Scenario | min_contour_area | min_consecutive_frames | cooldown_seconds |
    |---|---|---|---|
    | Entrance / office | 4,000 | 2 | 10 |
    | Parking | 12,000 | 2 | 15 |
    | Street with trees | 8,000 | 3 | 5 |
    | Maximum sensitivity | 500 | 1 | 0 |
    """

    enabled: bool = Field(
        default=True,
        description=(
            "`true` — надсилати кадр тільки при виявленому русі (економія ресурсів).\n"
            "`false` — надсилати **кожен** кадр."
        ),
    )
    min_contour_area: int = Field(
        default=4000, ge=100,
        description=(
            "Мін. площа об'єкта (px²). Листя < 500, людина ~3000–15000, авто ~10000+.\n"
            "Збільш якщо багато хибних спрацювань від дерев."
        ),
    )
    min_total_area: int = Field(
        default=6000, ge=100,
        description="Мін. сумарна площа всіх об'єктів (px²). Захист від шелесту листя.",
    )
    min_solidity: float = Field(
        default=0.4, ge=0.1, le=1.0,
        description="Мін. «щільність» форми (area / convex_hull). Листя ~0.3, люди ~0.6–0.95.",
    )
    min_consecutive_frames: int = Field(
        default=2, ge=1, le=10,
        description="Кадрів підряд для підтвердження. `1`=миттєво, `3+`=фільтр вітру.",
    )
    cooldown_seconds: float = Field(
        default=10.0, ge=0.0,
        description="Секунди після зупинки руху — продовжувати надсилати кадри.",
    )
    blur_size: int = Field(
        default=21, ge=3,
        description="Розмір Gaussian blur (тільки непарні). Більше = менше шуму камери.",
    )
    diff_threshold: int = Field(
        default=25, ge=1, le=255,
        description="Поріг бінаризації різниці кадрів. Менше = чутливіше до змін.",
    )
    dilate_iterations: int = Field(
        default=2, ge=1, le=5,
        description="Ітерації dilate. З'єднує розрізнені частини об'єкта в одну область.",
    )
    background_update_alpha: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description=(
            "Швидкість адаптації фону. "
            "`0.01`=стабільне освітлення, `0.05`=вулиця, `0.2`=змінне освітлення."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "🏠 Стандарт (вхід / офіс)",
                    "value": {
                        "enabled": True, "min_contour_area": 4000, "min_total_area": 6000,
                        "min_solidity": 0.4, "min_consecutive_frames": 2,
                        "cooldown_seconds": 10.0, "blur_size": 21, "diff_threshold": 25,
                        "dilate_iterations": 2, "background_update_alpha": 0.05,
                    },
                },
                {
                    "summary": "🚗 Паркінг",
                    "value": {
                        "enabled": True, "min_contour_area": 12000, "min_total_area": 18000,
                        "min_consecutive_frames": 2, "cooldown_seconds": 15.0,
                    },
                },
                {
                    "summary": "🌳 Вулиця з деревами",
                    "value": {
                        "enabled": True, "min_contour_area": 8000, "min_total_area": 12000,
                        "min_consecutive_frames": 3, "cooldown_seconds": 5.0,
                        "background_update_alpha": 0.03,
                    },
                },
                {
                    "summary": "🔴 Вимкнути детекцію (надсилати кожен кадр)",
                    "value": {"enabled": False},
                },
            ]
        }
    }
