from domain.repositories.event_repo import EventRepository
from domain.entities.event import SecurityEvent
from domain.enums.risk_enum import RiskLevel
from infrastructure.database import SessionLocal
from infrastructure.models.event_model import EventModel


class EventRepositoryImpl(EventRepository):

    def save(self, event: SecurityEvent) -> SecurityEvent:
        db = SessionLocal()
        try:
            existing = db.query(EventModel).filter(EventModel.id == event.id).first()
            if not existing:
                model = EventModel(
                    id=event.id,
                    camera_id=event.camera_id,
                    event_type=event.event_type,
                    object_class=event.object_class,
                    track_id=event.track_id,
                    confidence=event.confidence,
                    timestamp=event.timestamp,
                    zone_id=event.zone_id,
                    zone_name=event.zone_name,
                    risk=event.risk.value,
                    bbox=event.bbox,
                    event_metadata=event.metadata,
                )
                db.add(model)
                db.commit()
        finally:
            db.close()
        return event

    def get_by_id(self, event_id: str) -> SecurityEvent | None:
        db = SessionLocal()
        try:
            model = db.query(EventModel).filter(EventModel.id == event_id).first()
        finally:
            db.close()

        if not model:
            return None

        return SecurityEvent(
            id=model.id,
            camera_id=model.camera_id,
            event_type=model.event_type,
            timestamp=model.timestamp,
            risk=RiskLevel(model.risk),
            object_class=model.object_class,
            track_id=model.track_id,
            confidence=model.confidence,
            zone_id=model.zone_id,
            zone_name=model.zone_name,
            bbox=model.bbox,
            metadata=model.event_metadata,
        )

    def get_all(self):
        db = SessionLocal()
        try:
            models = (
                db.query(EventModel)
                .order_by(EventModel.timestamp.desc())
                .all()
            )
        finally:
            db.close()

        return [
            SecurityEvent(
                id=m.id,
                camera_id=m.camera_id,
                event_type=m.event_type,
                timestamp=m.timestamp,
                risk=RiskLevel(m.risk),
                object_class=m.object_class,
                track_id=m.track_id,
                confidence=m.confidence,
                zone_id=m.zone_id,
                zone_name=m.zone_name,
                bbox=m.bbox,
                metadata=m.event_metadata,
            )
            for m in models
        ]
