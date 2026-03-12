from typing import Any, Dict, Optional, Protocol, Tuple

import numpy as np

from schemas.motion_config import MotionConfig


class IFrameProcessor(Protocol):
    """Protocol for processing a frame (e.g. motion detection, resizing)."""

    def process(
        self, frame: np.ndarray, current_time: float
    ) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Process the frame.
        Returns (should_keep, modified_frame).
        If should_keep is False, the frame is discarded.
        """
        ...

    def get_stats(self) -> Dict[str, Any]:
        """Return processor-specific statistics."""
        ...

    def update_config(
        self,
        resize_width: Optional[int] = None,
        motion: Optional[MotionConfig] = None,
    ) -> None:
        """Update processor parameters at runtime without restart."""
        ...
