from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any, Iterable, Sequence


Mode = str
RiskLevel = str


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(hour=int(hour), minute=int(minute))


def _to_datetime(value: datetime | float | int | None) -> datetime:
    if value is None:
        return datetime.utcnow()
    if isinstance(value, datetime):
        return value
    return datetime.fromtimestamp(float(value))


def _bbox_center(bbox: dict[str, float] | Sequence[float]) -> tuple[float, float]:
    if isinstance(bbox, dict):
        x1 = float(bbox["x1"])
        y1 = float(bbox["y1"])
        x2 = float(bbox["x2"])
        y2 = float(bbox["y2"])
    else:
        x1, y1, x2, y2 = (float(v) for v in bbox)
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def point_in_polygon(px: float, py: float, polygon: Sequence[Sequence[float]]) -> bool:
    inside = False
    j = len(polygon) - 1
    for i, current in enumerate(polygon):
        xi, yi = float(current[0]), float(current[1])
        xj, yj = float(polygon[j][0]), float(polygon[j][1])
        intersects = ((yi > py) != (yj > py)) and (
            px < (xj - xi) * (py - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


@dataclass(slots=True)
class TimeWindow:
    start: time
    end: time

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TimeWindow":
        return cls(start=_parse_hhmm(payload["start"]), end=_parse_hhmm(payload["end"]))

    def contains(self, t: time) -> bool:
        if self.start <= self.end:
            return self.start <= t < self.end
        return t >= self.start or t < self.end


@dataclass(slots=True)
class ZoneConfig:
    id: int
    camera_id: int
    name: str
    polygon: list[list[float]]
    time_windows: list[TimeWindow]
    base_mode: Mode
    relaxed_multiplier: float
    strict_multiplier: float
    medium_threshold: int
    high_threshold: int
    decay_per_second: float
    cooldown_seconds: float

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ZoneConfig":
        multipliers = payload.get("risk_multipliers", {})
        thresholds = payload.get("people_thresholds", {})
        accumulation = payload.get("accumulation", {})
        return cls(
            id=int(payload["id"]),
            camera_id=int(payload["camera_id"]),
            name=payload["name"],
            polygon=[[float(x), float(y)] for x, y in payload["polygon"]],
            time_windows=[TimeWindow.from_payload(w) for w in payload.get("time_windows", [])],
            base_mode=payload.get("base_mode", "STRICT").upper(),
            relaxed_multiplier=float(multipliers.get("relaxed", 0.3)),
            strict_multiplier=float(multipliers.get("strict", 1.5)),
            medium_threshold=int(thresholds.get("medium", 2)),
            high_threshold=int(thresholds.get("high", 5)),
            decay_per_second=float(accumulation.get("decay_per_second", 1.0)),
            cooldown_seconds=float(payload.get("cooldown_seconds", 5)),
        )

    def mode_at(self, now: datetime) -> Mode:
        current_time = now.time()
        if any(window.contains(current_time) for window in self.time_windows):
            return "RELAXED"
        return self.base_mode or "STRICT"


@dataclass(slots=True)
class Detection:
    camera_id: int
    object_id: int
    object_class: str
    bbox: dict[str, float] | Sequence[float]
    confidence: float
    timestamp: datetime

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        fallback_timestamp: datetime,
    ) -> "Detection":
        return cls(
            camera_id=int(payload["camera_id"]),
            object_id=int(payload["object_id"]),
            object_class=str(payload.get("class", payload.get("object_class", ""))),
            bbox=payload["bbox"],
            confidence=float(payload.get("confidence", 0.0)),
            timestamp=_to_datetime(payload.get("timestamp", fallback_timestamp)),
        )


@dataclass(slots=True)
class ZoneState:
    current_people_ids: set[int] = field(default_factory=set)
    entry_time: dict[int, datetime] = field(default_factory=dict)
    risk_score: float = 0.0
    last_event_timestamp: datetime | None = None
    last_update_timestamp: datetime | None = None


class SmartVideoAnalyticsEngine:
    def __init__(self) -> None:
        self._zones_by_camera: dict[int, list[ZoneConfig]] = {}
        self._state: dict[tuple[int, int], ZoneState] = {}

    def load_zones(self, zones: Iterable[ZoneConfig | dict[str, Any]]) -> None:
        by_camera: dict[int, list[ZoneConfig]] = {}
        for item in zones:
            zone = item if isinstance(item, ZoneConfig) else ZoneConfig.from_payload(item)
            by_camera.setdefault(zone.camera_id, []).append(zone)
            self._state.setdefault((zone.camera_id, zone.id), ZoneState())
        self._zones_by_camera = by_camera

    def process_frame(
        self,
        detections: Sequence[Detection | dict[str, Any]],
        *,
        zones: Sequence[ZoneConfig | dict[str, Any]] | None = None,
        frame_timestamp: datetime | float | int | None = None,
        camera_ids: Sequence[int | str] | None = None,
    ) -> list[dict[str, Any]]:
        now = _to_datetime(frame_timestamp)
        if zones is not None:
            self.load_zones(zones)

        parsed: list[Detection] = [
            item if isinstance(item, Detection) else Detection.from_payload(item, now)
            for item in detections
        ]

        by_camera: dict[int, list[Detection]] = {}
        for detection in parsed:
            by_camera.setdefault(detection.camera_id, []).append(detection)

        if camera_ids:
            for camera_id in camera_ids:
                by_camera.setdefault(int(camera_id), [])

        events: list[dict[str, Any]] = []
        for camera_id, camera_detections in by_camera.items():
            camera_zones = self._zones_by_camera.get(camera_id, [])
            for zone in camera_zones:
                event = self._evaluate_zone(zone, camera_detections, now)
                if event:
                    events.append(event)
        return events

    def get_zone_state(self, camera_id: int | str, zone_id: int | str) -> ZoneState:
        return self._state.setdefault((int(camera_id), int(zone_id)), ZoneState())

    def _evaluate_zone(
        self,
        zone: ZoneConfig,
        detections: Sequence[Detection],
        now: datetime,
    ) -> dict[str, Any] | None:
        state = self._state.setdefault((zone.camera_id, zone.id), ZoneState())
        people_inside: list[Detection] = []

        for detection in detections:
            if detection.object_class != "person":
                continue
            center_x, center_y = _bbox_center(detection.bbox)
            if point_in_polygon(center_x, center_y, zone.polygon):
                people_inside.append(detection)

        current_ids = {d.object_id for d in people_inside}
        entered = current_ids - state.current_people_ids
        left = state.current_people_ids - current_ids

        for object_id in entered:
            state.entry_time[object_id] = now
        for object_id in left:
            state.entry_time.pop(object_id, None)
        state.current_people_ids = current_ids

        elapsed = 0.0
        if state.last_update_timestamp is not None:
            elapsed = max((now - state.last_update_timestamp).total_seconds(), 0.0)
        state.last_update_timestamp = now

        people_count = len(current_ids)
        mode = zone.mode_at(now)
        if people_count > 0:
            multiplier = zone.relaxed_multiplier if mode == "RELAXED" else zone.strict_multiplier
            increase = people_count * multiplier * (elapsed if elapsed > 0 else 1.0)
            state.risk_score += increase
        else:
            state.risk_score -= zone.decay_per_second * elapsed

        if state.risk_score < 0:
            state.risk_score = 0.0

        if people_count == 0:
            return None

        if not self._can_emit(state, now, zone.cooldown_seconds):
            return None

        state.last_event_timestamp = now
        risk_score_level = self._score_level(state.risk_score)
        smart_level = self._smart_level(zone=zone, mode=mode, people_count=people_count)
        risk_level = self._max_level(risk_score_level, smart_level)

        return {
            "camera_id": zone.camera_id,
            "zone_id": zone.id,
            "people_count": people_count,
            "mode": mode,
            "risk_level": risk_level,
            "risk_score": round(state.risk_score, 2),
            "timestamp": now,
        }

    @staticmethod
    def _can_emit(state: ZoneState, now: datetime, cooldown_seconds: float) -> bool:
        if state.last_event_timestamp is None:
            return True
        return (now - state.last_event_timestamp).total_seconds() >= cooldown_seconds

    @staticmethod
    def _score_level(risk_score: float) -> RiskLevel:
        if risk_score < 5:
            return "LOW"
        if risk_score < 15:
            return "MEDIUM"
        if risk_score < 30:
            return "HIGH"
        return "CRITICAL"

    @staticmethod
    def _smart_level(zone: ZoneConfig, mode: Mode, people_count: int) -> RiskLevel:
        if mode == "STRICT":
            if people_count >= 2:
                return "CRITICAL"
            if people_count == 1:
                return "HIGH"
            return "LOW"

        if people_count >= zone.high_threshold:
            return "HIGH"
        if people_count >= zone.medium_threshold:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _max_level(first: RiskLevel, second: RiskLevel) -> RiskLevel:
        order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        return first if order[first] >= order[second] else second
