from typing import Optional
from pydantic import BaseModel, Field, field_validator


class MotionConfig(BaseModel):
    """
    Configuration for the background-subtraction based motion detector.

    The detector compares each frame to an adaptive background model.
    It triggers when objects of a certain size (area) and density (solidity)
    are detected consistently over several frames.
    """

    enabled: bool = Field(
        default=True,
        description=(
            "`true` — send frame only when motion is detected (saves resources).\n"
            "`false` — send **every** frame (constant stream)."
        ),
    )
    min_contour_area: int = Field(
        default=4000, ge=100,
        description=(
            "Minimum area of a single moving object (px²). \n"
            "Increase to ignore small movements like insects or birds. \n"
            "Typical values: Human ~3000-15000, Car ~10000+."
        ),
    )
    min_total_area: int = Field(
        default=5000, ge=100,
        description=(
            "Minimum total area of ALL moving objects (px²). \n"
            "Helps filter out multiple small movements (e.g. rustling leaves) \n"
            "that individually pass `min_contour_area` but shouldn't trigger motion."
        ),
    )
    min_solidity: float = Field(
        default=0.3, ge=0.1, le=1.0,
        description=(
            "Minimum shape 'solidity' (area / convex_hull). \n"
            "Solid objects like humans or cars have high solidity (>0.5). \n"
            "Fragmented noise like leaves or rain have low solidity (<0.3)."
        ),
    )
    min_consecutive_frames: int = Field(
        default=2, ge=1, le=10,
        description=(
            "Number of consecutive frames where motion must be present to trigger an event. \n"
            "`1` = instant trigger, `3+` = robust filter against wind gusts or quick light changes."
        ),
    )
    cooldown_seconds: float = Field(
        default=5.0, ge=0.0,
        description="Number of seconds to continue sending frames after motion has stopped.",
    )
    blur_size: int = Field(
        default=15, ge=3,
        description=(
            "Size of Gaussian blur applied to the frame (must be odd). \n"
            "Larger values reduce digital camera noise but make detection of small objects harder."
        ),
    )
    diff_threshold: int = Field(
        default=25, ge=1, le=255,
        description=(
            "Difference threshold for detecting changes between frame and background. \n"
            "Lower = more sensitive. `20-30` is standard for most conditions."
        ),
    )
    dilate_iterations: int = Field(
        default=2, ge=1, le=5,
        description=(
            "Number of mathematical dilation passes. \n"
            "Helps connect fragmented object parts (e.g. a person's limbs) into a single area."
        ),
    )
    background_update_alpha: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description=(
            "Speed at which the background adaptively updates when no motion is detected. \n"
            "`0.01` = very slow (stable indoor lighting), \n"
            "`0.05` = standard (street/outdoor), \n"
            "`0.1+` = fast (variable lighting/clouds)."
        ),
    )




class MotionUpdateRequest(BaseModel):
    """
    Utility model for partial updates of motion configuration.
    All fields are optional. Descriptions are duplicated for Swagger visibility.
    """
    enabled: Optional[bool] = Field(default=None, description="Enable or disable motion detection.")
    min_contour_area: Optional[int] = Field(
        default=None, ge=100,
        description="Min area of a single moving object (px²)."
    )
    min_total_area: Optional[int] = Field(
        default=None, ge=100,
        description="Min total area of ALL moving objects (px²)."
    )
    min_solidity: Optional[float] = Field(
        default=None, ge=0.1, le=1.0,
        description="Min solidity (area / convex_hull). 0.1-1.0."
    )
    min_consecutive_frames: Optional[int] = Field(
        default=None, ge=1, le=10,
        description="Number of consecutive frames for motion confirmation."
    )
    cooldown_seconds: Optional[float] = Field(
        default=None, ge=0.0,
        description="Seconds to keep recording after motion stops."
    )
    blur_size: Optional[int] = Field(
        default=None, ge=3,
        description="Gaussian blur size (must be odd). Larger = less noise."
    )
    diff_threshold: Optional[int] = Field(
        default=None, ge=1, le=255,
        description="Frame difference threshold. Lower = more sensitive."
    )
    dilate_iterations: Optional[int] = Field(
        default=None, ge=1, le=5,
        description="Number of dilation passes to connect object parts."
    )
    background_update_alpha: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Background adaptation speed (0-1)."
    )

    @field_validator("blur_size")
    @classmethod
    def blur_size_must_be_odd(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v % 2 == 0:
            raise ValueError("blur_size must be an odd integer")
        return v
