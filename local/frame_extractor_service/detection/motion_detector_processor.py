"""
MotionDetectorProcessor — handles resizing and motion detection.

Combines resize + motion detection to match the workflow where
resize happens before motion detection.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import cv2
import numpy as np

from core.interfaces.i_frame_processor import IFrameProcessor
from detection.motion_detector import MotionDetector, MotionDetectorConfig
from schemas import MotionConfig


def _schema_to_detector_config(s: MotionConfig) -> MotionDetectorConfig:
    return MotionDetectorConfig(
        enabled=s.enabled,
        min_contour_area=s.min_contour_area,
        min_total_area=s.min_total_area,
        min_solidity=s.min_solidity,
        min_consecutive_frames=s.min_consecutive_frames,
        cooldown_seconds=s.cooldown_seconds,
        blur_size=s.blur_size,
        diff_threshold=s.diff_threshold,
        dilate_iterations=s.dilate_iterations,
        background_update_alpha=s.background_update_alpha,
    )


class MotionDetectorProcessor(IFrameProcessor):
    """
    Handles resizing and motion detection.
    Combining them here to match the old workflow where resize
    happens before motion detection.
    """

    def __init__(self, motion_config: MotionConfig, resize_width: int) -> None:
        self.resize_width = resize_width
        self.motion_config_schema = motion_config
        self._motion_detector = MotionDetector(_schema_to_detector_config(motion_config))

    def update_config(
        self,
        resize_width: Optional[int] = None,
        motion: Optional[MotionConfig] = None,
    ) -> None:
        """Update processor parameters at runtime without restart."""
        if resize_width is not None:
            self.resize_width = resize_width
        if motion is not None:
            self.motion_config_schema = motion
            self._motion_detector.update_config(_schema_to_detector_config(motion))

    def process(
        self, frame: np.ndarray, current_time: float
    ) -> Tuple[bool, Optional[np.ndarray]]:
        # 1. Resize
        processed_frame = frame
        if self.resize_width > 0:
            h, w = processed_frame.shape[:2]
            if w != self.resize_width:
                new_h = int(h * self.resize_width / w)
                processed_frame = cv2.resize(
                    processed_frame, (self.resize_width, new_h)
                )

        # 2. Motion Detection
        should_send = (
            self._motion_detector.detect(processed_frame, current_time)
            if self.motion_config_schema.enabled
            else True
        )

        return should_send, processed_frame

    def get_stats(self) -> Dict[str, Any]:
        return self._motion_detector.get_stats()
