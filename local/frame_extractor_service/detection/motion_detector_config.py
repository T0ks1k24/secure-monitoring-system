from dataclasses import dataclass

@dataclass
class MotionDetectorConfig:
    enabled: bool = True
    min_contour_area: int = 4000
    min_total_area: int = 6000
    min_solidity: float = 0.4
    min_consecutive_frames: int = 2
    cooldown_seconds: float = 10.0
    blur_size: int = 21
    diff_threshold: int = 25
    dilate_iterations: int = 2
    background_update_alpha: float = 0.05
