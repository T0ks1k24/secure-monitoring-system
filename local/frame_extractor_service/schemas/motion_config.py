from typing import Optional
from pydantic import BaseModel, Field, field_validator


class MotionConfig(BaseModel):
    """
    Motion detector setup based on **background model**.

    The detector compares each frame to the background model (not the previous frame).
    The background is updated slowly when quiet (`background_update_alpha`).
    """

    enabled: bool = Field(
        default=True,
        description=(
            "`true` — send frame only when motion is detected (saves resources).\n"
            "`false` — send **every** frame."
        ),
    )
    min_contour_area: int = Field(
        default=4000, ge=100,
        description=(
            "Min object area (px²). Leaves < 500, human ~3000–15000, car ~10000+.\n"
            "Increase if there are many false positives from trees."
        ),
    )
    min_total_area: int = Field(
        default=6000, ge=100,
        description="Min total area of all objects (px²). Filter for rustling leaves.",
    )
    min_solidity: float = Field(
        default=0.4, ge=0.1, le=1.0,
        description="Min shape 'solidity' (area / convex_hull). Leaves ~0.3, humans ~0.6–0.95.",
    )
    min_consecutive_frames: int = Field(
        default=2, ge=1, le=10,
        description="Consecutive frames for confirmation. `1`=instant, `3+`=wind filter.",
    )
    cooldown_seconds: float = Field(
        default=10.0, ge=0.0,
        description="Seconds after motion stops — continue sending frames.",
    )
    blur_size: int = Field(
        default=21, ge=3,
        description="Gaussian blur size (odd only). Larger = less camera noise.",
    )
    diff_threshold: int = Field(
        default=25, ge=1, le=255,
        description="Frame difference binarization threshold. Lower = more sensitive.",
    )
    dilate_iterations: int = Field(
        default=2, ge=1, le=5,
        description="Dilate iterations. Connects fragmented object parts into one area.",
    )
    background_update_alpha: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description=(
            "Background adaptation speed. "
            "`0.01`=stable lighting, `0.05`=street, `0.2`=variable lighting."
        ),
    )

    @field_validator("blur_size")
    @classmethod
    def blur_size_must_be_odd(cls, v: int) -> int:
        if v % 2 == 0:
            raise ValueError("blur_size must be an odd integer")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "🏠 Standard (Entrance / Office)",
                    "value": {
                        "enabled": True, "min_contour_area": 4000, "min_total_area": 6000,
                        "min_solidity": 0.4, "min_consecutive_frames": 2,
                        "cooldown_seconds": 10.0, "blur_size": 21, "diff_threshold": 25,
                        "dilate_iterations": 2, "background_update_alpha": 0.05,
                    },
                },
                {
                    "summary": "🚗 Parking",
                    "value": {
                        "enabled": True, "min_contour_area": 12000, "min_total_area": 18000,
                        "min_consecutive_frames": 2, "cooldown_seconds": 15.0,
                    },
                }
            ]
        }
    }


class MotionUpdateRequest(BaseModel):
    """Optional fields for partial motion config updates."""
    enabled: Optional[bool] = None
    min_contour_area: Optional[int] = Field(default=None, ge=100)
    min_total_area: Optional[int] = Field(default=None, ge=100)
    min_solidity: Optional[float] = Field(default=None, ge=0.1, le=1.0)
    min_consecutive_frames: Optional[int] = Field(default=None, ge=1, le=10)
    cooldown_seconds: Optional[float] = Field(default=None, ge=0.0)
    blur_size: Optional[int] = Field(default=None, ge=3)
    diff_threshold: Optional[int] = Field(default=None, ge=1, le=255)
    dilate_iterations: Optional[int] = Field(default=None, ge=1, le=5)
    background_update_alpha: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    @field_validator("blur_size")
    @classmethod
    def blur_size_must_be_odd(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v % 2 == 0:
            raise ValueError("blur_size must be an odd integer")
        return v
