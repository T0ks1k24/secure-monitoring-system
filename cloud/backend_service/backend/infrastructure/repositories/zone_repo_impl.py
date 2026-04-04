from infrastructure.database import SessionLocal
from infrastructure.models.zone_model import ZoneModel
from domain.entities.zone import Zone

class ZoneRepositoryImpl:

    def create(self, data):
        db = SessionLocal()

        zone = ZoneModel(
            name=data.name,
            camera_id=data.camera_id,
            polygon=data.polygon,
            zone_type=data.zone_type,
            risk_weight=data.risk_weight,
            is_active=data.is_active,
            max_people_allowed=data.max_people_allowed,
            time_windows=[window.model_dump() for window in data.time_windows],
            base_mode=data.base_mode,
            risk_multipliers=data.risk_multipliers.model_dump(),
            people_thresholds=data.people_thresholds.model_dump(),
            accumulation=data.accumulation.model_dump(),
            cooldown_seconds=data.cooldown_seconds,
        )

        db.add(zone)
        db.commit()
        db.refresh(zone)
        db.close()

        return zone

    def get_by_camera(self, camera_id: str):
        db = SessionLocal()
        zones = db.query(ZoneModel).filter(
            ZoneModel.camera_id == camera_id,
            ZoneModel.is_active == True
        ).all()
        db.close()
        return zones

    def update(self, zone_id, data):
        db = SessionLocal()
        zone = db.query(ZoneModel).filter(ZoneModel.id == zone_id).first()

        if not zone:
            db.close()
            return None

        updates = data.model_dump(exclude_none=True)
        for field, value in updates.items():
            if hasattr(zone, field):
                setattr(zone, field, value)

        db.commit()
        db.refresh(zone)
        db.close()

        return zone

    def delete(self, zone_id):
        db = SessionLocal()
        zone = db.query(ZoneModel).filter(ZoneModel.id == zone_id).first()

        if not zone:
            db.close()
            return False

        db.delete(zone)
        db.commit()
        db.close()

        return True
