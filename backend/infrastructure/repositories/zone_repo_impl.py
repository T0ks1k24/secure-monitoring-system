import uuid
from domain.repositories.zone_repo import ZoneRepository
from domain.entities.zone import Zone
from infrastructure.database import SessionLocal
from infrastructure.models.zone_model import ZoneModel


class ZoneRepositoryImpl(ZoneRepository):

    def save(self, zone: Zone) -> Zone:

        db = SessionLocal()

        model = ZoneModel(
            id=zone.id,
            name=zone.name,
            coordinates=zone.coordinates,
            max_people_allowed=zone.max_people_allowed
        )

        db.add(model)
        db.commit()
        db.close()

        return zone

    def update(self, zone: Zone) -> Zone:

        db = SessionLocal()

        model = db.query(ZoneModel).filter(ZoneModel.id == zone.id).first()

        model.name = zone.name
        model.coordinates = zone.coordinates
        model.max_people_allowed = zone.max_people_allowed

        db.commit()
        db.close()

        return zone

    def get_by_id(self, zone_id: uuid.UUID) -> Zone | None:

        db = SessionLocal()
        model = db.query(ZoneModel).filter(ZoneModel.id == zone_id).first()
        db.close()

        if not model:
            return None

        return Zone(
            id=model.id,
            name=model.name,
            coordinates=model.coordinates,
            max_people_allowed=model.max_people_allowed
        )

    def get_all(self):

        db = SessionLocal()
        models = db.query(ZoneModel).all()
        db.close()

        return [
            Zone(
                id=m.id,
                name=m.name,
                coordinates=m.coordinates,
                max_people_allowed=m.max_people_allowed
            )
            for m in models
        ]

    def delete(self, zone_id: uuid.UUID) -> None:

        db = SessionLocal()
        db.query(ZoneModel).filter(ZoneModel.id == zone_id).delete()
        db.commit()
        db.close()
