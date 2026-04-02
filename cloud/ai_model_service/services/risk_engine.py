"""
Risk Engine — серце відеоаналітики.

Отримує підтверджені треки + зони → оцінює ризик → генерує SecurityEvent.

Логіка ризиків:
  1. Зональні правила (ZoneRule) — основа, конфігуруються на фронтенді
  2. Траєкторний аналіз — швидкість, напрям, зависання
  3. Зброя — завжди CRITICAL незалежно від зон і розкладів
  4. RiskSchedule — знижує ризик у робочі вікна часу (per-zone)
  5. Дедуплікація — не генеруємо одну подію двічі за короткий час
"""
from __future__ import annotations

import math
import time
import uuid
import logging
from datetime import datetime, time as dtime
from typing import Dict, List, Optional, Set, Tuple

from schemas.events import (
    SecurityEvent, EventType, RiskLevel,
    Zone, ZoneType, ZoneRule, RiskSchedule, TrackedObject, BoundingBox,
)
from services.tracker import Track
from models.detector import WEAPON_CLASSES, VEHICLE_CLASSES
from config.settings import settings

logger = logging.getLogger(__name__)


# ── Risk level ordering ───────────────────────────────────────────────────────

# Порядок рівнів ризику від найнижчого до найвищого
_RISK_ORDER: List[RiskLevel] = [
    RiskLevel.LOW,
    RiskLevel.MEDIUM,
    RiskLevel.HIGH,
    RiskLevel.CRITICAL,
]
_RISK_INDEX: Dict[RiskLevel, int] = {r: i for i, r in enumerate(_RISK_ORDER)}


def reduce_risk(level: RiskLevel, steps: int) -> RiskLevel:
    """
    Знижує рівень ризику на `steps` рівнів вниз.
    Мінімум — LOW. CRITICAL → HIGH (steps=1), CRITICAL → MEDIUM (steps=2), etc.
    """
    idx = max(0, _RISK_INDEX[level] - steps)
    return _RISK_ORDER[idx]


# ── Risk Schedule Evaluator ───────────────────────────────────────────────────

class RiskScheduleEvaluator:
    """
    Перевіряє чи поточний момент потрапляє у вікно зниження ризику.

    Підтримує:
      - Звичайні вікна: "08:00"–"17:00" (start < end)
      - Нічні вікна: "22:00"–"06:00"   (start > end, перетин північ)
      - Фільтр по днях тижня: days=[0,1,2,3,4] (пн–пт)
      - Timezone через zoneinfo (stdlib Python 3.9+), fallback до UTC

    WEAPON_DETECTED ніколи не знижується — логіка в RiskEngine._apply_schedule.
    """

    def get_active_schedule(
        self,
        schedules: List[RiskSchedule],
        now: Optional[datetime] = None,
    ) -> Optional[RiskSchedule]:
        """
        Повертає перше активне вікно розкладу або None.
        Якщо кілька вікон перекриваються — береться те з більшим reduce_by.
        """
        if not schedules:
            return None

        if now is None:
            now = datetime.now()

        active = [s for s in schedules if self._is_active(s, now)]
        if not active:
            return None

        # Якщо кілька активних — беремо максимальне зниження
        return max(active, key=lambda s: s.reduce_by)

    def _is_active(self, schedule: RiskSchedule, now: datetime) -> bool:
        # ── Перевірка дня тижня ──────────────────────────────────
        if schedule.days is not None:
            # Python weekday(): 0=пн, 6=нд
            weekday = self._local_weekday(schedule, now)
            if weekday not in schedule.days:
                return False

        # ── Поточний час у локальній timezone ───────────────────
        local_now = self._local_time(schedule, now)
        start = self._parse_time(schedule.time_start)
        end   = self._parse_time(schedule.time_end)

        # ── Перевірка вікна часу ─────────────────────────────────
        if start <= end:
            # Звичайне вікно: "08:00"–"17:00"
            return start <= local_now < end
        else:
            # Нічне вікно через північ: "22:00"–"06:00"
            # Активно якщо: local_now >= 22:00 АБО local_now < 06:00
            return local_now >= start or local_now < end

    def _local_time(self, schedule: RiskSchedule, now: datetime) -> dtime:
        """Повертає поточний час з урахуванням timezone."""
        if schedule.timezone:
            try:
                from zoneinfo import ZoneInfo
                local_dt = now.astimezone(ZoneInfo(schedule.timezone))
                return local_dt.time().replace(second=0, microsecond=0)
            except Exception:
                logger.warning(
                    f"Unknown timezone '{schedule.timezone}', falling back to local"
                )
        return now.time().replace(second=0, microsecond=0)

    def _local_weekday(self, schedule: RiskSchedule, now: datetime) -> int:
        if schedule.timezone:
            try:
                from zoneinfo import ZoneInfo
                return now.astimezone(ZoneInfo(schedule.timezone)).weekday()
            except Exception:
                pass
        return now.weekday()

    @staticmethod
    def _parse_time(t: str) -> dtime:
        """Парсить "HH:MM" в datetime.time."""
        h, m = t.split(":")
        return dtime(int(h), int(m))


schedule_evaluator = RiskScheduleEvaluator()


# ── Deduplication ─────────────────────────────────────────────────────────────

class EventDeduplicator:
    """
    Запобігає генерації однакових подій занадто часто.
    Ключ: (camera_id, event_type, track_id, zone_id)
    """
    COOLDOWN: Dict[EventType, float] = {
        EventType.ZONE_INTRUSION:      10.0,
        EventType.WEAPON_DETECTED:      5.0,
        EventType.RUNNING_DETECTED:    15.0,
        EventType.ZONE_LOITERING:      30.0,
        EventType.ZONE_CROWDING:       20.0,
        EventType.DIRECTION_VIOLATION: 15.0,
        EventType.ABANDONED_OBJECT:    60.0,
    }
    DEFAULT_COOLDOWN = 10.0

    def __init__(self) -> None:
        self._last_fired: Dict[tuple, float] = {}

    def should_fire(
        self,
        camera_id: str,
        event_type: EventType,
        track_id: Optional[int],
        zone_id: Optional[str],
    ) -> bool:
        key = (camera_id, event_type, track_id, zone_id)
        last = self._last_fired.get(key, 0.0)
        cooldown = self.COOLDOWN.get(event_type, self.DEFAULT_COOLDOWN)
        if (time.monotonic() - last) >= cooldown:
            self._last_fired[key] = time.monotonic()
            return True
        return False

    def clear_camera(self, camera_id: str) -> None:
        to_del = [k for k in self._last_fired if k[0] == camera_id]
        for k in to_del:
            del self._last_fired[k]


deduplicator = EventDeduplicator()


# ── Default zone rules ────────────────────────────────────────────────────────

DEFAULT_ZONE_RULES: Dict[ZoneType, List[ZoneRule]] = {
    ZoneType.RESTRICTED: [
        ZoneRule(
            object_class="*",
            risk_level=RiskLevel.HIGH,
            event_type=EventType.ZONE_INTRUSION,
            trigger_after_seconds=0.0,
        ),
    ],
    ZoneType.PEDESTRIAN: [
        ZoneRule(
            object_class="car",
            risk_level=RiskLevel.HIGH,
            event_type=EventType.ZONE_INTRUSION,
        ),
        ZoneRule(
            object_class="truck",
            risk_level=RiskLevel.HIGH,
            event_type=EventType.ZONE_INTRUSION,
        ),
        ZoneRule(
            object_class="motorcycle",
            risk_level=RiskLevel.MEDIUM,
            event_type=EventType.ZONE_INTRUSION,
        ),
    ],
    ZoneType.PARKING: [
        ZoneRule(
            object_class="person",
            risk_level=RiskLevel.MEDIUM,
            event_type=EventType.ZONE_INTRUSION,
            trigger_after_seconds=30.0,
        ),
    ],
    ZoneType.PERIMETER: [
        ZoneRule(
            object_class="*",
            risk_level=RiskLevel.MEDIUM,
            event_type=EventType.ZONE_INTRUSION,
            trigger_after_seconds=0.0,
        ),
    ],
    ZoneType.ENTRANCE: [
        ZoneRule(
            object_class="person",
            risk_level=RiskLevel.LOW,
            event_type=EventType.PERSON_DETECTED,
        ),
    ],
    ZoneType.SAFE_ZONE: [],
}


def _get_effective_rules(zone: Zone) -> List[ZoneRule]:
    if zone.rules:
        return zone.rules
    return DEFAULT_ZONE_RULES.get(zone.zone_type, [])


# ── Risk Engine ───────────────────────────────────────────────────────────────

class RiskEngine:
    """
    Аналізує підтверджені треки та зони → генерує SecurityEvent.
    """

    def analyze(
        self,
        camera_id: str,
        tracks: List[Track],
        zone_memberships: Dict[int, List[Zone]],
        frame_timestamp: float,
        fps: float = 10.0,
    ) -> List[SecurityEvent]:
        events: List[SecurityEvent] = []

        # Час аналізу (один раз для всього кадру — консистентність)
        now = datetime.now()

        # 1. Зброя (вищий пріоритет — завжди CRITICAL, ніколи не знижується)
        for track in tracks:
            if track.obj_class in WEAPON_CLASSES:
                evt = self._weapon_event(camera_id, track, frame_timestamp)
                if evt:
                    events.append(evt)

        # 2. Зональний аналіз
        for track in tracks:
            track_zones = zone_memberships.get(track.id, [])
            if settings.RISK_EVENTS_ONLY_IN_ZONES and not track_zones:
                continue
            zone_events = self._zone_analysis(
                camera_id, track, track_zones, frame_timestamp, fps, now
            )
            events.extend(zone_events)

        # 3. Поведінковий аналіз
        for track in tracks:
            track_zones = zone_memberships.get(track.id, [])
            if settings.RISK_EVENTS_ONLY_IN_ZONES and not track_zones:
                continue
            behavioral = self._behavioral_analysis(
                camera_id, track, track_zones, frame_timestamp, fps, now
            )
            events.extend(behavioral)

        # 4. Crowding
        crowding = self._crowding_analysis(
            camera_id, tracks, zone_memberships, frame_timestamp, now
        )
        events.extend(crowding)

        return events

    # ── Schedule helper ───────────────────────────────────────────

    def _apply_schedule(
        self,
        event_type: EventType,
        risk_level: RiskLevel,
        zone: Zone,
        now: datetime,
    ) -> Tuple[RiskLevel, Optional[RiskSchedule]]:
        """
        Застосовує активний розклад до рівня ризику події.

        WEAPON_DETECTED → завжди CRITICAL, ніколи не знижується.
        Решта → знижуємо на reduce_by рівнів якщо є активне вікно.

        Returns: (effective_risk_level, active_schedule_or_None)
        """
        # Зброя — жодних поблажок
        if event_type == EventType.WEAPON_DETECTED:
            return risk_level, None

        active = schedule_evaluator.get_active_schedule(zone.risk_schedules, now)
        if active is None:
            return risk_level, None

        reduced = reduce_risk(risk_level, active.reduce_by)
        if reduced != risk_level:
            label = active.label or f"{active.time_start}–{active.time_end}"
            logger.debug(
                f"Risk reduced {risk_level}→{reduced} "
                f"(schedule: '{label}', zone: {zone.name})"
            )
        return reduced, active

    # ── 1. Weapon ─────────────────────────────────────────────────

    def _weapon_event(
        self,
        camera_id: str,
        track: Track,
        timestamp: float,
    ) -> Optional[SecurityEvent]:
        if not deduplicator.should_fire(
            camera_id, EventType.WEAPON_DETECTED, track.id, None
        ):
            return None
        logger.warning(
            f"[{camera_id}] ⚠️  WEAPON detected: {track.obj_class} track={track.id}"
        )
        return SecurityEvent(
            event_id=str(uuid.uuid4()),
            camera_id=camera_id,
            timestamp=timestamp,
            event_type=EventType.WEAPON_DETECTED,
            risk_level=RiskLevel.CRITICAL,
            track_id=track.id,
            object_class=track.obj_class,
            confidence=track.confidence,
            bbox=track.bbox,
            metadata={
                "speed": track.speed,
                "age_frames": track.age_frames,
                "schedule_applied": False,  # зброя — завжди без знижки
            },
        )

    # ── 2. Zone analysis ──────────────────────────────────────────

    def _zone_analysis(
        self,
        camera_id: str,
        track: Track,
        zones: List[Zone],
        timestamp: float,
        fps: float,
        now: datetime,
    ) -> List[SecurityEvent]:
        events = []
        for zone in zones:
            rules = _get_effective_rules(zone)
            for rule in rules:
                if rule.object_class != "*" and rule.object_class != track.obj_class:
                    if rule.object_class == "vehicle" and track.obj_class not in VEHICLE_CLASSES:
                        continue
                    elif rule.object_class != "vehicle":
                        continue

                dwell = track.get_dwell_seconds(zone.id)
                if dwell < rule.trigger_after_seconds:
                    continue

                if not deduplicator.should_fire(
                    camera_id, rule.event_type, track.id, zone.id
                ):
                    continue

                effective_risk, active_schedule = self._apply_schedule(
                    rule.event_type, rule.risk_level, zone, now
                )

                logger.info(
                    f"[{camera_id}] Zone event: {rule.event_type} "
                    f"track={track.id} cls={track.obj_class} "
                    f"zone={zone.name} risk={effective_risk} "
                    f"(base={rule.risk_level}) dwell={dwell:.1f}s"
                )

                meta: Dict = {
                    "dwell_seconds": dwell,
                    "zone_type": zone.zone_type,
                    "speed": track.speed,
                    "base_risk_level": rule.risk_level,
                    "schedule_applied": active_schedule is not None,
                }
                if active_schedule:
                    meta["schedule_label"] = (
                        active_schedule.label
                        or f"{active_schedule.time_start}–{active_schedule.time_end}"
                    )
                    meta["schedule_reduce_by"] = active_schedule.reduce_by

                events.append(SecurityEvent(
                    event_id=str(uuid.uuid4()),
                    camera_id=camera_id,
                    timestamp=timestamp,
                    event_type=rule.event_type,
                    risk_level=effective_risk,
                    track_id=track.id,
                    object_class=track.obj_class,
                    confidence=track.confidence,
                    bbox=track.bbox,
                    zone_id=zone.id,
                    zone_name=zone.name,
                    metadata=meta,
                ))

            # Loitering
            if zone.max_dwell_seconds:
                dwell = track.get_dwell_seconds(zone.id)
                if dwell >= zone.max_dwell_seconds:
                    if deduplicator.should_fire(
                        camera_id, EventType.ZONE_LOITERING, track.id, zone.id
                    ):
                        base_risk = RiskLevel.MEDIUM
                        effective_risk, active_schedule = self._apply_schedule(
                            EventType.ZONE_LOITERING, base_risk, zone, now
                        )
                        meta = {
                            "dwell_seconds": dwell,
                            "base_risk_level": base_risk,
                            "schedule_applied": active_schedule is not None,
                        }
                        if active_schedule:
                            meta["schedule_label"] = (
                                active_schedule.label
                                or f"{active_schedule.time_start}–{active_schedule.time_end}"
                            )
                        events.append(SecurityEvent(
                            event_id=str(uuid.uuid4()),
                            camera_id=camera_id,
                            timestamp=timestamp,
                            event_type=EventType.ZONE_LOITERING,
                            risk_level=effective_risk,
                            track_id=track.id,
                            object_class=track.obj_class,
                            confidence=track.confidence,
                            bbox=track.bbox,
                            zone_id=zone.id,
                            zone_name=zone.name,
                            metadata=meta,
                        ))
        return events

    # ── 3. Behavioral ─────────────────────────────────────────────

    def _behavioral_analysis(
        self,
        camera_id: str,
        track: Track,
        zones: List[Zone],
        timestamp: float,
        fps: float,
        now: datetime,
    ) -> List[SecurityEvent]:
        events = []
        if settings.RISK_EVENTS_ONLY_IN_ZONES and not zones:
            return events

        # === Running ===
        RUNNING_THRESHOLD = 0.018
        primary_zone = zones[0] if zones else None
        if (
            track.obj_class == "person"
            and track.speed > RUNNING_THRESHOLD
            and track.age_frames > 5
        ):
            if deduplicator.should_fire(
                camera_id, EventType.RUNNING_DETECTED, track.id, primary_zone.id if primary_zone else None
            ):
                base_risk = RiskLevel.MEDIUM
                # Для behavioral подій без зони — беремо найагресивніший розклад
                # серед зон де зараз перебуває об'єкт
                effective_risk = self._reduce_for_zones(
                    EventType.RUNNING_DETECTED, base_risk, zones, now
                )
                events.append(SecurityEvent(
                    event_id=str(uuid.uuid4()),
                    camera_id=camera_id,
                    timestamp=timestamp,
                    event_type=EventType.RUNNING_DETECTED,
                    risk_level=effective_risk,
                    track_id=track.id,
                    object_class=track.obj_class,
                    confidence=track.confidence,
                    bbox=track.bbox,
                    zone_id=primary_zone.id if primary_zone else None,
                    zone_name=primary_zone.name if primary_zone else None,
                    metadata={
                        "speed_norm": track.speed,
                        "direction": track.direction_degrees,
                        "base_risk_level": base_risk,
                        "schedule_applied": effective_risk != base_risk,
                    },
                ))

        # === Direction violation ===
        for zone in zones:
            if zone.allowed_direction is None:
                continue
            direction = track.direction_degrees
            if direction is None:
                continue
            diff = abs(direction - zone.allowed_direction) % 360
            if diff > 180:
                diff = 360 - diff
            if diff > zone.allowed_direction_tolerance:
                if deduplicator.should_fire(
                    camera_id, EventType.DIRECTION_VIOLATION, track.id, zone.id
                ):
                    base_risk = RiskLevel.MEDIUM
                    effective_risk, active_schedule = self._apply_schedule(
                        EventType.DIRECTION_VIOLATION, base_risk, zone, now
                    )
                    events.append(SecurityEvent(
                        event_id=str(uuid.uuid4()),
                        camera_id=camera_id,
                        timestamp=timestamp,
                        event_type=EventType.DIRECTION_VIOLATION,
                        risk_level=effective_risk,
                        track_id=track.id,
                        object_class=track.obj_class,
                        confidence=track.confidence,
                        bbox=track.bbox,
                        zone_id=zone.id,
                        zone_name=zone.name,
                        metadata={
                            "actual_direction": direction,
                            "allowed_direction": zone.allowed_direction,
                            "angle_diff": diff,
                            "base_risk_level": base_risk,
                            "schedule_applied": active_schedule is not None,
                        },
                    ))

        # === Abandoned object ===
        ABANDONED_CLASSES = {"backpack", "handbag", "suitcase"}
        ABANDONED_MIN_FRAMES = int(30 * fps)
        ABANDONED_MAX_SPEED = 0.001

        if (
            track.obj_class in ABANDONED_CLASSES
            and track.age_frames > ABANDONED_MIN_FRAMES
            and track.speed < ABANDONED_MAX_SPEED
        ):
            if deduplicator.should_fire(
                camera_id, EventType.ABANDONED_OBJECT, track.id, primary_zone.id if primary_zone else None
            ):
                base_risk = RiskLevel.HIGH
                effective_risk = self._reduce_for_zones(
                    EventType.ABANDONED_OBJECT, base_risk, zones, now
                )
                events.append(SecurityEvent(
                    event_id=str(uuid.uuid4()),
                    camera_id=camera_id,
                    timestamp=timestamp,
                    event_type=EventType.ABANDONED_OBJECT,
                    risk_level=effective_risk,
                    track_id=track.id,
                    object_class=track.obj_class,
                    confidence=track.confidence,
                    bbox=track.bbox,
                    zone_id=primary_zone.id if primary_zone else None,
                    zone_name=primary_zone.name if primary_zone else None,
                    metadata={
                        "stationary_frames": track.age_frames,
                        "stationary_seconds": track.age_frames / fps,
                        "base_risk_level": base_risk,
                        "schedule_applied": effective_risk != base_risk,
                    },
                ))

        return events

    # ── 4. Crowding ───────────────────────────────────────────────

    def _crowding_analysis(
        self,
        camera_id: str,
        tracks: List[Track],
        zone_memberships: Dict[int, List[Zone]],
        timestamp: float,
        now: datetime,
    ) -> List[SecurityEvent]:
        events = []
        zone_counts: Dict[str, Dict[str, int]] = {}
        zone_objects: Dict[str, Zone] = {}

        for track in tracks:
            for zone in zone_memberships.get(track.id, []):
                if zone.id not in zone_counts:
                    zone_counts[zone.id] = {}
                    zone_objects[zone.id] = zone
                zone_counts[zone.id][track.obj_class] = (
                    zone_counts[zone.id].get(track.obj_class, 0) + 1
                )

        for zone_id, counts in zone_counts.items():
            zone = zone_objects[zone_id]
            rules = _get_effective_rules(zone)
            for rule in rules:
                if rule.max_count is None:
                    continue
                cls_count = (
                    sum(counts.values()) if rule.object_class == "*"
                    else counts.get(rule.object_class, 0)
                )
                if cls_count > rule.max_count:
                    if deduplicator.should_fire(
                        camera_id, EventType.ZONE_CROWDING, None, zone_id
                    ):
                        base_risk = rule.risk_level
                        effective_risk, active_schedule = self._apply_schedule(
                            EventType.ZONE_CROWDING, base_risk, zone, now
                        )
                        meta = {
                            "count": cls_count,
                            "max_count": rule.max_count,
                            "object_class": rule.object_class,
                            "breakdown": counts,
                            "base_risk_level": base_risk,
                            "schedule_applied": active_schedule is not None,
                        }
                        if active_schedule:
                            meta["schedule_label"] = (
                                active_schedule.label
                                or f"{active_schedule.time_start}–{active_schedule.time_end}"
                            )
                        events.append(SecurityEvent(
                            event_id=str(uuid.uuid4()),
                            camera_id=camera_id,
                            timestamp=timestamp,
                            event_type=EventType.ZONE_CROWDING,
                            risk_level=effective_risk,
                            zone_id=zone_id,
                            zone_name=zone.name,
                            metadata=meta,
                        ))
        return events

    # ── Helpers ───────────────────────────────────────────────────

    def _reduce_for_zones(
        self,
        event_type: EventType,
        base_risk: RiskLevel,
        zones: List[Zone],
        now: datetime,
    ) -> RiskLevel:
        """
        Для подій без конкретної зони (running, abandoned) —
        беремо максимальне зниження серед усіх зон де зараз об'єкт.
        """
        if not zones:
            return base_risk
        best_reduce = 0
        for zone in zones:
            active = schedule_evaluator.get_active_schedule(zone.risk_schedules, now)
            if active:
                best_reduce = max(best_reduce, active.reduce_by)
        if best_reduce > 0:
            return reduce_risk(base_risk, best_reduce)
        return base_risk


risk_engine = RiskEngine()
