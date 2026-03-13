from dataclasses import dataclass

@dataclass
class MotionState:
    is_active: bool = False
    raw_motion: bool = False
    consecutive_frames: int = 0
    last_confirmed_time: float = 0.0
    total_events: int = 0
