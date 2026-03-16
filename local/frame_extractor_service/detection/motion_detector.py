"""
MotionDetector — motion detector based on a background model.

Does not require any imports from frame_extractor_service —
only cv2 and numpy. Safely tested without pydantic/fastapi.
"""
from __future__ import annotations

import cv2
import logging
import numpy as np
from typing import Optional

from .motion_detector_config import MotionDetectorConfig
from .motion_state import MotionState


class MotionDetector:
    """
    Motion detector based on adaptive background model.

    Usage:
        detector = MotionDetector()
        should_send = detector.detect(frame, time.monotonic())
    """

    def __init__(self, config: Optional[MotionDetectorConfig] = None) -> None:
        self.config = config or MotionDetectorConfig()
        self._background: Optional[np.ndarray] = None
        self.state = MotionState()

    def reset(self) -> None:
        """Resets state and background. Call on camera reconnect."""
        self._background = None
        self.state = MotionState()

    def update_config(self, config: MotionDetectorConfig) -> None:
        self.config = config

    def detect(self, frame: np.ndarray, current_time: float) -> bool:
        """
        Analyzes the frame. Returns True if frame should be sent to AI.
        True = confirmed motion exists OR still within cooldown.
        """
        raw = self._compute_raw_motion(frame)

        if raw:
            self.state.raw_motion = True
            self.state.consecutive_frames += 1
        else:
            self.state.raw_motion = False
            self.state.consecutive_frames = 0

        confirmed = self.state.consecutive_frames >= self.config.min_consecutive_frames

        if confirmed:
            if not self.state.is_active:
                self.state.is_active = True
                self.state.total_events += 1
                logger.info(
                    "Motion confirmed (event #%d, %d consecutive frames)",
                    self.state.total_events,
                    self.state.consecutive_frames,
                )
            self.state.last_confirmed_time = current_time

        in_cooldown = (
            self.state.last_confirmed_time > 0.0
            and (current_time - self.state.last_confirmed_time) < self.config.cooldown_seconds
        )

        # BUG FIX #2: keep is_active=True during cooldown period
        should_send = confirmed or in_cooldown
        self.state.is_active = should_send

        # Update background only when quiet (no motion and not in cooldown)
        if not should_send and not raw and self._background is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(
                gray, (self.config.blur_size, self.config.blur_size), 0
            ).astype(np.float32)
            alpha = self.config.background_update_alpha
            self._background = cv2.addWeighted(
                self._background.astype(np.float32), 1.0 - alpha,
                gray, alpha, 0,
            ).astype(np.uint8)

        return should_send

    def get_stats(self) -> dict:
        return {
            "motion_detected": self.state.is_active,
            "total_motion_events": self.state.total_events,
            "consecutive_frames": self.state.consecutive_frames,
        }

    def _compute_raw_motion(self, frame: np.ndarray) -> bool:
        """Returns True if there is "raw" motion in the current frame."""
        cfg = self.config
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (cfg.blur_size, cfg.blur_size), 0)

        if self._background is None:
            self._background = gray.copy()
            return False

        diff = cv2.absdiff(self._background, gray)
        _, thresh = cv2.threshold(diff, cfg.diff_threshold, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        thresh = cv2.dilate(thresh, kernel, iterations=cfg.dilate_iterations)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return False

        total_area = 0
        significant = 0
        for c in contours:
            area = cv2.contourArea(c)
            if area < cfg.min_contour_area:
                continue
            hull_area = cv2.contourArea(cv2.convexHull(c))
            if hull_area > 0 and (area / hull_area) < cfg.min_solidity:
                continue
            total_area += area
            significant += 1

        if significant == 0 or total_area < cfg.min_total_area:
            return False

        logger.debug("Raw motion: %d contours, total_area=%d", significant, total_area)
        return True


logger = logging.getLogger(__name__)
