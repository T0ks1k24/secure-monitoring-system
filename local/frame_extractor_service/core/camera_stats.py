from dataclasses import dataclass

@dataclass
class CameraStats:
    frames_sent: int = 0
    frames_failed: int = 0
    frames_skipped: int = 0
