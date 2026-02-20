import uuid
from domain.repositories.event_repo import EventRepository
from domain.entities.event import SecurityEvent
from domain.enums.risk_enum import RiskLevel
from infrastructure.database import SessionLocal
from infrastructure.models.event_model import EventModel


class EventRepositoryImpl(EventRepository):

    def save(self, event: SecurityEvent) -> SecurityEvent:

        db = SessionLocal()

        model = EventModel(
            id=event.id,
            camera_id=event.camera_id,
            persons=event.persons,
            zone_id=event.zone_id,
            timestamp=event.timestamp,
            risk=event.risk.value
        )

        db.add(model)
        db.commit()
        db.close()

        return event

    def get_by_id(self, event_id: uuid.UUID) -> SecurityEvent | None:

        db = SessionLocal()
        model = db.query(EventModel).filter(EventModel.id == event_id).first()
        db.close()

        if not model:
            return None

        return SecurityEvent(
            id=model.id,
            camera_id=model.camera_id,
            persons=model.persons,
            zone_id=model.zone_id,
            timestamp=model.timestamp,
            risk=RiskLevel(model.risk)
        )

    def get_all(self):

        db = SessionLocal()
        models = db.query(EventModel).all()
        db.close()

        return [
            SecurityEvent(
                id=m.id,
                camera_id=m.camera_id,
                persons=m.persons,
                zone_id=m.zone_id,
                timestamp=m.timestamp,
                risk=RiskLevel(m.risk)
            )
            for m in models
        ]
