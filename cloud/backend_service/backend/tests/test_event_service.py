from application.dto.ai_event_dto import AIEventDTO
from application.services.event_service import EventService
from domain.enums.risk_enum import RiskLevel


class FakeRepo:
    def __init__(self) -> None:
        self.saved = None

    def save(self, event):
        self.saved = event
        return event


def test_ingest_ai_event_maps_payload_to_domain_event():
    repo = FakeRepo()
    service = EventService(repo=repo)

    dto = AIEventDTO(
        event_id="evt-1",
        camera_id="cam-1",
        timestamp=1710000000.0,
        event_type="zone_intrusion",
        risk_level="high",
        track_id=12,
        object_class="person",
        confidence=0.91,
        zone_id="zone-1",
        zone_name="Restricted",
        bbox={"x1": 0.1, "y1": 0.2, "x2": 0.3, "y2": 0.4},
        metadata={"source": "test"},
    )

    event = service.ingest_ai_event(dto)

    assert repo.saved is event
    assert event.id == "evt-1"
    assert event.camera_id == "cam-1"
    assert event.event_type == "zone_intrusion"
    assert event.risk == RiskLevel.HIGH
    assert event.object_class == "person"
    assert event.zone_name == "Restricted"
    assert event.bbox == {"x1": 0.1, "y1": 0.2, "x2": 0.3, "y2": 0.4}
