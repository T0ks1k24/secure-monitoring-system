from __future__ import annotations

import cv2
import numpy as np
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MotionConfig:
    enabled: bool = True
    min_contour_area: int = 4000
    min_total_area: int = 6000
    min_solidity: float = 0.4
    min_consecutive_frames: int = 2
    cooldown_seconds: float = 10.0
    blur_size: int = 21
    diff_threshold: int = 25
    dilate_iterations: int = 2
    # Швидкість оновлення фону (0.0–1.0).
    # 0.05 = повільна адаптація (рекомендовано для продакшну).
    # 1.0  = миттєве оновлення (зручно для тестів).
    background_update_alpha: float = 0.05


@dataclass
class MotionState:
    is_active: bool = False
    raw_motion: bool = False
    consecutive_frames: int = 0
    last_confirmed_time: float = 0.0
    total_events: int = 0


class MotionDetector:
    """
    Детектор руху з фільтрацією хибних спрацювань від вітру/дерев.

    Використовує background model: порівнює з фоном (не з попереднім кадром).
    Переваги:
      - Нерухомий об'єкт в кадрі ЗАЛИШАЄТЬСЯ «рухом» відносно фону.
      - Зникнення об'єкта не перезапускає cooldown (фон не оновлюється під час руху).

    Ланцюжок фільтрів:
      1. GaussianBlur         → прибирає піксельний шум камери
      2. absdiff(frame, bg)   → зміни відносно фону
      3. threshold + dilate   → бінарна маска
      4. min_contour_area     → відкидає дрібні (листя)
      5. min_solidity         → відкидає хаотичні форми (листя)
      6. min_total_area       → відкидає шелест (багато дрібних разом)
      7. min_consecutive_frames → відкидає короткі пориви вітру
    """

    def __init__(self, config: Optional[MotionConfig] = None) -> None:
        self.config = config or MotionConfig()
        self._background: Optional[np.ndarray] = None
        self.state = MotionState()

    def reset(self) -> None:
        """Скидає стан і background — викликати при реконнекті камери."""
        self._background = None
        self.state = MotionState()

    def update_config(self, config: MotionConfig) -> None:
        self.config = config

    def detect(self, frame: np.ndarray, current_time: float) -> bool:
        """
        Аналізує кадр. Повертає True якщо треба надсилати на AI.
        Надсилаємо якщо: є підтверджений рух АБО ще в межах cooldown.
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
                    f"Motion confirmed (event #{self.state.total_events}, "
                    f"{self.state.consecutive_frames} consecutive frames)"
                )
            self.state.last_confirmed_time = current_time
        else:
            if self.state.is_active:
                logger.debug("Motion stopped")
            self.state.is_active = False

        in_cooldown = (
            self.state.last_confirmed_time > 0.0
            and (current_time - self.state.last_confirmed_time) < self.config.cooldown_seconds
        )

        should_send = confirmed or in_cooldown

        # Оновлюємо background ТІЛЬКИ коли АБСОЛЮТНО тихо:
        # немає сирого руху, немає підтвердженого руху, не в cooldown.
        # Якщо є навіть raw_motion — чекаємо, щоб не «забути» фон передчасно.
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

    # ──────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────

    def _compute_raw_motion(self, frame: np.ndarray) -> bool:
        cfg = self.config

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (cfg.blur_size, cfg.blur_size), 0)

        # Перший кадр — ініціалізуємо background
        if self._background is None:
            self._background = gray.copy()
            return False

        diff = cv2.absdiff(self._background, gray)

        _, thresh = cv2.threshold(diff, cfg.diff_threshold, 255, cv2.THRESH_BINARY)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        thresh = cv2.dilate(thresh, kernel, iterations=cfg.dilate_iterations)

        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return False

        total_area = 0
        significant_count = 0

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < cfg.min_contour_area:
                continue

            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            if hull_area > 0:
                solidity = area / hull_area
                if solidity < cfg.min_solidity:
                    continue

            total_area += area
            significant_count += 1

        if significant_count == 0:
            return False

        if total_area < cfg.min_total_area:
            return False

        logger.debug(f"Raw motion: {significant_count} contours, total_area={total_area}")
        return True
