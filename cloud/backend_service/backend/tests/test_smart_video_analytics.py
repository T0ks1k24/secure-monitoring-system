
from datetime import datetime, timedelta

from application.services.smart_video_analytics import SmartVideoAnalyticsEngine


def _zone_payload(*, camera_id: int, zone_id: int, cooldown: int = 0) -> dict:
    return {
        "id": zone_id,
        "camera_id": camera_id,
        "name": f"Zone {zone_id}",
        "polygon": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]],
        "time_windows": [
            {"start": "09:00", "end": "10:00"},
            {"start": "13:00", "end": "14:00"},
            {"start": "18:00", "end": "19:00"},
        ],
        "base_mode": "STRICT",
        "risk_multipliers": {"relaxed": 0.3, "strict": 1.5},
        "people_thresholds": {"medium": 2, "high": 5},
        "accumulation": {"decay_per_second": 1.0},
        "cooldown_seconds": cooldown,
    }


def _person(camera_id: int, object_id: int) -> dict:
    return {
        "camera_id": camera_id,
        "object_id": object_id,
        "class": "person",
        "bbox": {"x1": 0.3, "y1": 0.3, "x2": 0.4, "y2": 0.5},
        "confidence": 0.95,
    }


def test_mode_switch_affects_risk_level_for_same_action():
    engine = SmartVideoAnalyticsEngine()
    zone = _zone_payload(camera_id=1, zone_id=10)

    relaxed_ts = datetime(2026, 4, 4, 9, 30, 0)
    relaxed_event = engine.process_frame(
        [_person(camera_id=1, object_id=1)],
        zones=[zone],
        frame_timestamp=relaxed_ts,
    )[0]

    strict_ts = datetime(2026, 4, 4, 11, 30, 0)
    strict_event = engine.process_frame(
        [_person(camera_id=1, object_id=2)],
        frame_timestamp=strict_ts,
    )[0]

    assert relaxed_event["mode"] == "RELAXED"
    assert relaxed_event["risk_level"] == "LOW"
    assert strict_event["mode"] == "STRICT"
    assert strict_event["risk_level"] in {"HIGH", "CRITICAL"}


def test_multiple_time_windows_respected():
    engine = SmartVideoAnalyticsEngine()
    zone = _zone_payload(camera_id=1, zone_id=11)
    engine.load_zones([zone])

    relaxed_event = engine.process_frame(
        [_person(camera_id=1, object_id=1)],
        frame_timestamp=datetime(2026, 4, 4, 13, 15, 0),
    )[0]
    strict_event = engine.process_frame(
        [_person(camera_id=1, object_id=2)],
        frame_timestamp=datetime(2026, 4, 4, 15, 0, 0),
    )[0]

    assert relaxed_event["mode"] == "RELAXED"
    assert strict_event["mode"] == "STRICT"


def test_risk_accumulates_and_decays():
    engine = SmartVideoAnalyticsEngine()
    zone = _zone_payload(camera_id=1, zone_id=12)
    start = datetime(2026, 4, 4, 11, 0, 0)

    event1 = engine.process_frame(
        [_person(camera_id=1, object_id=1)],
        zones=[zone],
        frame_timestamp=start,
    )[0]
    event2 = engine.process_frame(
        [_person(camera_id=1, object_id=1)],
        frame_timestamp=start + timedelta(seconds=2),
    )[0]
    engine.process_frame(
        [],
        frame_timestamp=start + timedelta(seconds=4),
        camera_ids=[1],
    )

    state = engine.get_zone_state(1, 12)
    assert event2["risk_score"] > event1["risk_score"]
    assert state.risk_score < event2["risk_score"]
    assert state.risk_score >= 0


def test_cooldown_blocks_spam():
    engine = SmartVideoAnalyticsEngine()
    zone = _zone_payload(camera_id=1, zone_id=13, cooldown=5)
    start = datetime(2026, 4, 4, 11, 0, 0)

    first = engine.process_frame(
        [_person(camera_id=1, object_id=1)],
        zones=[zone],
        frame_timestamp=start,
    )
    second = engine.process_frame(
        [_person(camera_id=1, object_id=1)],
        frame_timestamp=start + timedelta(seconds=2),
    )
    third = engine.process_frame(
        [_person(camera_id=1, object_id=1)],
        frame_timestamp=start + timedelta(seconds=5),
    )

    assert len(first) == 1
    assert len(second) == 0
    assert len(third) == 1


def test_object_entry_and_exit_tracking():
    engine = SmartVideoAnalyticsEngine()
    zone = _zone_payload(camera_id=1, zone_id=14)
    start = datetime(2026, 4, 4, 11, 0, 0)

    engine.process_frame(
        [_person(camera_id=1, object_id=10)],
        zones=[zone],
        frame_timestamp=start,
    )
    state = engine.get_zone_state(1, 14)
    assert 10 in state.entry_time

    engine.process_frame(
        [_person(camera_id=1, object_id=10), _person(camera_id=1, object_id=11)],
        frame_timestamp=start + timedelta(seconds=1),
    )
    assert 11 in state.entry_time

    engine.process_frame(
        [],
        frame_timestamp=start + timedelta(seconds=2),
        camera_ids=[1],
    )
    assert state.entry_time == {}
    assert state.current_people_ids == set()


def test_multi_camera_processing_isolated():
    engine = SmartVideoAnalyticsEngine()
    zones = [_zone_payload(camera_id=1, zone_id=20), _zone_payload(camera_id=2, zone_id=21)]

    events = engine.process_frame(
        [_person(camera_id=1, object_id=1), _person(camera_id=2, object_id=2)],
        zones=zones,
        frame_timestamp=datetime(2026, 4, 4, 11, 0, 0),
    )

    assert len(events) == 2
    by_camera = {event["camera_id"]: event for event in events}
    assert by_camera[1]["zone_id"] == 20
    assert by_camera[2]["zone_id"] == 21
