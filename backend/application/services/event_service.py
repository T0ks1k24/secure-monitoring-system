from domain.repositories.event_repo import EventRepository
from domain.repositories.zone_repo import ZoneRepository
from application.services.risk_service import RiskService
from domain.entities.event import SecurityEvent
from application.dto.ai_event_dto import AIEventDTO


class EventService:

    def __init__(
        self,
        event_repo: EventRepository,
        zone_repo: ZoneRepository,
        risk_service: RiskService
    ):
        self.event_repo = event_repo
        self.zone_repo = zone_repo
        self.risk_service = risk_service

    def process_ai_event(self, dto: AIEventDTO):

        zone = self.zone_repo.get_by_id(dto.zone_id)

        risk = self.risk_service.evaluate(
            persons=dto.persons_detected,
            zone_limit=zone.max_people_allowed
        )

        event = SecurityEvent(
            camera_id=dto.camera_id,
            persons=dto.persons_detected,
            zone_id=dto.zone_id,
            timestamp=dto.timestamp,
            risk=risk
        )

        self.event_repo.save(event)

        return event
