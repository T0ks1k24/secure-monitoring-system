from application.dto.zone_dto import ZoneCreateDTO, ZoneUpdateDTO


def test_zone_create_dto_supports_analytics_config():
    dto = ZoneCreateDTO(
        name="Zone A",
        camera_id="1",
        polygon=[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9]],
        zone_type="restricted",
        risk_weight=25.0,
        is_active=True,
        max_people_allowed=3,
        time_windows=[{"start": "09:00", "end": "10:00"}],
        base_mode="STRICT",
        risk_multipliers={"relaxed": 0.2, "strict": 1.7},
        people_thresholds={"medium": 2, "high": 5},
        accumulation={"decay_per_second": 0.8},
        cooldown_seconds=6,
    )

    assert dto.time_windows[0].start == "09:00"
    assert dto.risk_multipliers.strict == 1.7
    assert dto.people_thresholds.high == 5
    assert dto.accumulation.decay_per_second == 0.8
    assert dto.cooldown_seconds == 6


def test_zone_update_dto_accepts_partial_analytics_config():
    dto = ZoneUpdateDTO(
        base_mode="STRICT",
        risk_multipliers={"relaxed": 0.4, "strict": 2.0},
        cooldown_seconds=10,
    )

    assert dto.base_mode == "STRICT"
    assert dto.risk_multipliers is not None
    assert dto.risk_multipliers.relaxed == 0.4
    assert dto.cooldown_seconds == 10


def test_zone_create_dto_normalizes_legacy_zone_type_aliases():
    dto = ZoneCreateDTO(
        name="Zone Alias",
        camera_id="1",
        polygon=[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9]],
        zone_type="danger",
        risk_weight=25.0,
        is_active=True,
        max_people_allowed=1,
    )

    assert dto.zone_type == "restricted"


def test_zone_update_dto_normalizes_legacy_zone_type_aliases():
    dto = ZoneUpdateDTO(zone_type="safe")

    assert dto.zone_type == "safe_zone"
