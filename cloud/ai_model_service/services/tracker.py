"""
Простий IoU-базований трекер об'єктів.
Один екземпляр на кожну камеру — керується через TrackerRegistry.

Чому не ByteTrack/SORT: вони потребують scipy/lap як залежності.
Цей трекер реалізує ту саму core-логіку (IoU matching + Kalman-like prediction)
і достатній для security analytics.
"""
from __future__ import annotations

import math
import time
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np

from schemas.events import BoundingBox, TrackedObject
from config.settings import settings

logger = logging.getLogger(__name__)


class Track:
    """Один трек — один об'єкт що спостерігається."""

    _id_counter = 0

    def __init__(self, bbox: BoundingBox, obj_class: str, confidence: float) -> None:
        Track._id_counter += 1
        self.id = Track._id_counter

        self.obj_class = obj_class
        self.confidence = confidence
        self.bbox = bbox

        # Траєкторія: список (cx, cy) у нормалізованих координатах
        self.trajectory: List[Tuple[float, float]] = [(bbox.cx, bbox.cy)]
        self.age_frames: int = 1
        self.hits: int = 1           # скільки разів підтверджено детекцією
        self.misses: int = 0         # скільки кадрів підряд без детекції

        # Velocity для prediction (exponential moving average)
        self._vx: float = 0.0
        self._vy: float = 0.0
        self._ema_alpha: float = 0.4

        # Час входу в кожну зону {zone_id: enter_timestamp}
        self._zone_enter_time: Dict[str, float] = {}
        # Накопичений час перебування {zone_id: total_seconds}
        self.dwell_time: Dict[str, float] = defaultdict(float)

    @property
    def is_confirmed(self) -> bool:
        return self.hits >= settings.TRACKER_MIN_HITS

    @property
    def cx(self) -> float:
        return self.bbox.cx

    @property
    def cy(self) -> float:
        return self.bbox.cy

    def update(self, bbox: BoundingBox, obj_class: str, confidence: float) -> None:
        """Оновлення треку новою детекцією."""
        # Velocity EMA
        dx = bbox.cx - self.bbox.cx
        dy = bbox.cy - self.bbox.cy
        self._vx = self._ema_alpha * dx + (1 - self._ema_alpha) * self._vx
        self._vy = self._ema_alpha * dy + (1 - self._ema_alpha) * self._vy

        self.bbox = bbox
        self.obj_class = obj_class
        self.confidence = max(self.confidence, confidence)  # беремо найвищу

        # Зберігаємо траєкторію (обмеження по довжині)
        self.trajectory.append((bbox.cx, bbox.cy))
        if len(self.trajectory) > settings.TRAJECTORY_HISTORY_FRAMES:
            self.trajectory.pop(0)

        self.age_frames += 1
        self.hits += 1
        self.misses = 0

    def predict(self) -> BoundingBox:
        """Прогнозує позицію на наступний кадр за velocity."""
        return BoundingBox(
            x1=self.bbox.x1 + self._vx,
            y1=self.bbox.y1 + self._vy,
            x2=self.bbox.x2 + self._vx,
            y2=self.bbox.y2 + self._vy,
        )

    @property
    def speed(self) -> float:
        """Поточна швидкість (евклідова норма velocity у norm.coords)."""
        return math.sqrt(self._vx ** 2 + self._vy ** 2)

    @property
    def direction_degrees(self) -> Optional[float]:
        """
        Напрям руху в градусах.
        0° = вгору (північ), 90° = вправо, 180° = вниз, 270° = вліво.
        """
        if len(self.trajectory) < 3:
            return None
        # Беремо вектор від -3 до останнього
        p1 = self.trajectory[-3]
        p2 = self.trajectory[-1]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return None
        # atan2 дає кут від осі X, конвертуємо в "compass bearing"
        angle = math.degrees(math.atan2(dx, -dy)) % 360
        return angle

    def enter_zone(self, zone_id: str) -> None:
        if zone_id not in self._zone_enter_time:
            self._zone_enter_time[zone_id] = time.monotonic()

    def exit_zone(self, zone_id: str) -> None:
        if zone_id in self._zone_enter_time:
            elapsed = time.monotonic() - self._zone_enter_time.pop(zone_id)
            self.dwell_time[zone_id] += elapsed

    def get_dwell_seconds(self, zone_id: str) -> float:
        """Поточний час перебування в зоні (включаючи поточну сесію)."""
        total = self.dwell_time.get(zone_id, 0.0)
        if zone_id in self._zone_enter_time:
            total += time.monotonic() - self._zone_enter_time[zone_id]
        return total

    def to_schema(self) -> TrackedObject:
        return TrackedObject(
            track_id=self.id,
            object_class=self.obj_class,
            confidence=self.confidence,
            bbox=self.bbox,
            trajectory=[[x, y] for x, y in self.trajectory],
            speed=self.speed,
            direction=self.direction_degrees,
            age_frames=self.age_frames,
            dwell_time=dict(self.dwell_time),
        )


# ── IoU utilities ─────────────────────────────────────────────────────────────

def _iou(a: BoundingBox, b: BoundingBox) -> float:
    ix1 = max(a.x1, b.x1)
    iy1 = max(a.y1, b.y1)
    ix2 = min(a.x2, b.x2)
    iy2 = min(a.y2, b.y2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    union = a.area + b.area - inter
    return inter / union if union > 0 else 0.0


def _hungarian_match(
    tracks: List[Track],
    detections: List[Tuple[BoundingBox, str, float]],
    iou_threshold: float,
) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """
    Простий greedy matching за IoU (O(T*D)).
    Для security cameras з невеликою кількістю об'єктів цього достатньо.
    Returns: (matched_pairs, unmatched_track_idx, unmatched_det_idx)
    """
    if not tracks or not detections:
        return [], list(range(len(tracks))), list(range(len(detections)))

    # Будуємо IoU матрицю
    iou_matrix = np.zeros((len(tracks), len(detections)))
    for t_idx, track in enumerate(tracks):
        pred_bbox = track.predict()
        for d_idx, (det_bbox, _, _) in enumerate(detections):
            iou_matrix[t_idx, d_idx] = _iou(pred_bbox, det_bbox)

    matched = []
    unmatched_t = list(range(len(tracks)))
    unmatched_d = list(range(len(detections)))

    # Жадібне: вибираємо найкращу пару поки є хороші IoU
    while True:
        if iou_matrix.max() < iou_threshold:
            break
        t_idx, d_idx = np.unravel_index(iou_matrix.argmax(), iou_matrix.shape)
        matched.append((int(t_idx), int(d_idx)))
        iou_matrix[t_idx, :] = -1
        iou_matrix[:, d_idx] = -1
        unmatched_t.remove(t_idx)
        unmatched_d.remove(d_idx)

    return matched, unmatched_t, unmatched_d


# ── Per-camera tracker ────────────────────────────────────────────────────────

class CameraTracker:
    """
    Трекер для однієї камери.
    Кожен кадр: update() → повертає список TrackedObject.
    """

    def __init__(self, camera_id: str, fps: float = 10.0) -> None:
        self.camera_id = camera_id
        self.fps = fps
        self._tracks: List[Track] = []
        # Зони в яких об'єкт перебував на попередньому кадрі
        self._prev_zone_memberships: Dict[int, set] = defaultdict(set)

    @property
    def max_misses(self) -> int:
        """Максимум пропущених кадрів до видалення треку."""
        return max(1, int(settings.TRACKER_MAX_AGE_SECONDS * self.fps))

    def update(
        self,
        detections: List[Tuple[BoundingBox, str, float]],
        active_zone_ids: List[str],
    ) -> List[Track]:
        """
        Оновлює трекер новими детекціями.
        active_zone_ids — зони в яких треба рахувати dwell_time.
        Returns: список підтверджених активних треків.
        """
        matched, unmatched_t, unmatched_d = _hungarian_match(
            self._tracks,
            detections,
            settings.TRACKER_IOU_THRESHOLD,
        )

        # Оновлюємо matched треки
        for t_idx, d_idx in matched:
            bbox, cls, conf = detections[d_idx]
            self._tracks[t_idx].update(bbox, cls, conf)

        # Збільшуємо misses для unmatched треків
        for t_idx in unmatched_t:
            self._tracks[t_idx].misses += 1
            self._tracks[t_idx].age_frames += 1

        # Створюємо нові треки для unmatched детекцій
        for d_idx in unmatched_d:
            bbox, cls, conf = detections[d_idx]
            self._tracks.append(Track(bbox, cls, conf))

        # Видаляємо мертві треки
        self._tracks = [t for t in self._tracks if t.misses <= self.max_misses]

        return [t for t in self._tracks if t.is_confirmed]

    def get_zone_events(
        self,
        confirmed_tracks: List[Track],
        zone_memberships: Dict[int, set],   # {track_id: set of zone_ids}
    ) -> Dict[int, Tuple[set, set]]:
        """
        Порівнює поточні memberships з попередніми.
        Returns: {track_id: (entered_zones, exited_zones)}
        """
        events: Dict[int, Tuple[set, set]] = {}
        all_track_ids = {t.id for t in confirmed_tracks}

        for track in confirmed_tracks:
            prev = self._prev_zone_memberships.get(track.id, set())
            curr = zone_memberships.get(track.id, set())

            entered = curr - prev
            exited  = prev - curr

            for zone_id in entered:
                track.enter_zone(zone_id)
            for zone_id in exited:
                track.exit_zone(zone_id)

            if entered or exited:
                events[track.id] = (entered, exited)

        # Виходимо з зон для треків що зникли
        for track_id, prev_zones in self._prev_zone_memberships.items():
            if track_id not in all_track_ids:
                track = next((t for t in self._tracks if t.id == track_id), None)
                if track:
                    for z in prev_zones:
                        track.exit_zone(z)

        self._prev_zone_memberships = {
            track.id: zone_memberships.get(track.id, set())
            for track in confirmed_tracks
        }
        return events

    def clear(self) -> None:
        self._tracks.clear()
        self._prev_zone_memberships.clear()


# ── Registry (один трекер на камеру) ─────────────────────────────────────────

class TrackerRegistry:
    """Зберігає по одному CameraTracker на camera_id."""

    def __init__(self) -> None:
        self._trackers: Dict[str, CameraTracker] = {}

    def get(self, camera_id: str, fps: float = 10.0) -> CameraTracker:
        if camera_id not in self._trackers:
            self._trackers[camera_id] = CameraTracker(camera_id, fps)
            logger.info(f"Created tracker for camera: {camera_id}")
        return self._trackers[camera_id]

    def remove(self, camera_id: str) -> None:
        self._trackers.pop(camera_id, None)

    @property
    def count(self) -> int:
        return len(self._trackers)


tracker_registry = TrackerRegistry()
