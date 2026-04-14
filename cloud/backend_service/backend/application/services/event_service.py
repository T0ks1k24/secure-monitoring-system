from application.dto.ai_event_dto import AIEventDTO
from domain.entities.event import SecurityEvent
from domain.enums.risk_enum import RiskLevel
from infrastructure.repositories.event_repo_impl import EventRepositoryImpl


class EventService:
    def __init__(self, repo: EventRepositoryImpl | None = None):
        self.repo = repo or EventRepositoryImpl()

    def ingest_ai_event(self, dto: AIEventDTO) -> SecurityEvent:
        event = SecurityEvent(
            id=dto.event_id,
            camera_id=dto.camera_id,
            event_type=dto.event_type,
            timestamp=dto.timestamp_as_datetime(),
            risk=RiskLevel.from_value(dto.risk_level),
            object_class=dto.object_class,
            track_id=dto.track_id,
            confidence=dto.confidence,
            zone_id=dto.zone_id,
            zone_name=dto.zone_name,
            bbox=dto.bbox.model_dump() if dto.bbox else None,
            metadata=dto.metadata,
        )
        return self.repo.save(event)
