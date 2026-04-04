from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Dict, List, Optional, Set

from schemas.events import EventType, RiskLevel, SecurityEvent, Zone
from services.tracker import Track


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def _risk_from_score(score: float) -> RiskLevel:
    if score < 5:
        return RiskLevel.LOW
    if score < 15:
        return RiskLevel.MEDIUM
    if score < 30:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def _max_risk(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    order = {
        RiskLevel.LOW: 0,
        RiskLevel.MEDIUM: 1,
        RiskLevel.HIGH: 2,
        RiskLevel.CRITICAL: 3,
    }
    return a if order[a] >= order[b] else b


@dataclass(slots=True)
class ZoneState:
    current_people_ids: Set[int] = field(default_factory=set)
    entry_time: Dict[int, datetime] = field(default_factory=dict)
    risk_score: float = 0.0
    last_event_timestamp: Optional[datetime] = None
    last_update_timestamp: Optional[datetime] = None


class SmartZoneAnalytics:
    def __init__(self) -> None:
        self._state: Dict[tuple[str, str], ZoneState] = {}

    def analyze(
        self,
        camera_id: str,
        zones: List[Zone],
        tracks: List[Track],
        zone_memberships: Dict[int, List[Zone]],
        frame_timestamp: float,
        fps: float = 10.0,
    ) -> List[SecurityEvent]:
        now = datetime.fromtimestamp(frame_timestamp)
        zone_people: Dict[str, Set[int]] = {zone.id: set() for zone in zones}

        track_by_id = {track.id: track for track in tracks}
        for track_id, track_zones in zone_memberships.items():
            track = track_by_id.get(track_id)
            if track is None or track.obj_class != "person":
                continue
            for zone in track_zones:
                zone_people.setdefault(zone.id, set()).add(track_id)

        events: List[SecurityEvent] = []
        for zone in zones:
            event = self._analyze_zone(
                camera_id=camera_id,
                zone=zone,
                people_ids=zone_people.get(zone.id, set()),
                now=now,
                frame_timestamp=frame_timestamp,
                fps=fps,
            )
            if event is not None:
                events.append(event)
        return events

    def _analyze_zone(
        self,
        camera_id: str,
        zone: Zone,
        people_ids: Set[int],
        now: datetime,
        frame_timestamp: float,
        fps: float,
    ) -> Optional[SecurityEvent]:
        state = self._state.setdefault((camera_id, zone.id), ZoneState())

        entered = people_ids - state.current_people_ids
        left = state.current_people_ids - people_ids
        for object_id in entered:
            state.entry_time[object_id] = now
        for object_id in left:
            state.entry_time.pop(object_id, None)
        state.current_people_ids = set(people_ids)

        elapsed = 1.0 / fps if fps > 0 else 0.1
        if state.last_update_timestamp is not None:
            elapsed = max((now - state.last_update_timestamp).total_seconds(), 0.0)
        state.last_update_timestamp = now

        people_count = len(people_ids)
        mode = self._mode_for_zone(zone, now)

        decay_per_second = float(zone.metadata.get("accumulation", {}).get("decay_per_second", 1.0))
        if people_count > 0:
            multipliers = zone.metadata.get("risk_multipliers", {})
            relaxed = float(multipliers.get("relaxed", 0.3))
            strict = float(multipliers.get("strict", 1.5))
            multiplier = relaxed if mode == "RELAXED" else strict
            state.risk_score += people_count * multiplier * elapsed
        else:
            state.risk_score -= decay_per_second * elapsed

        state.risk_score = max(0.0, state.risk_score)
        if people_count == 0:
            return None

        cooldown = float(zone.metadata.get("cooldown_seconds", 5))
        if (
            state.last_event_timestamp is not None
            and (now - state.last_event_timestamp).total_seconds() < cooldown
        ):
            return None

        state.last_event_timestamp = now
        score_level = _risk_from_score(state.risk_score)
        smart_level = self._smart_level(zone=zone, mode=mode, people_count=people_count)
        effective_level = _max_risk(score_level, smart_level)

        return SecurityEvent(
            event_id=str(uuid.uuid4()),
            camera_id=camera_id,
            timestamp=frame_timestamp,
            event_type=EventType.ZONE_SMART_ACTIVITY,
            risk_level=effective_level,
            zone_id=zone.id,
            zone_name=zone.name,
            metadata={
                "people_count": people_count,
                "mode": mode,
                "risk_score": round(state.risk_score, 2),
                "entry_time": {
                    str(object_id): entered_at.isoformat()
                    for object_id, entered_at in state.entry_time.items()
                },
            },
        )

    def _mode_for_zone(self, zone: Zone, now: datetime) -> str:
        windows = zone.metadata.get("time_windows", [])
        current_t = now.time()
        for window in windows:
            start = _parse_hhmm(window["start"])
            end = _parse_hhmm(window["end"])
            if start <= end:
                if start <= current_t < end:
                    return "RELAXED"
            else:
                if current_t >= start or current_t < end:
                    return "RELAXED"
        return str(zone.metadata.get("base_mode", "STRICT")).upper()

    @staticmethod
    def _smart_level(zone: Zone, mode: str, people_count: int) -> RiskLevel:
        if mode == "STRICT":
            if people_count >= 2:
                return RiskLevel.CRITICAL
            if people_count == 1:
                return RiskLevel.HIGH
            return RiskLevel.LOW

        thresholds = zone.metadata.get("people_thresholds", {})
        medium_threshold = int(thresholds.get("medium", 2))
        high_threshold = int(thresholds.get("high", 5))
        if people_count >= high_threshold:
            return RiskLevel.HIGH
        if people_count >= medium_threshold:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


smart_zone_analytics = SmartZoneAnalytics()
