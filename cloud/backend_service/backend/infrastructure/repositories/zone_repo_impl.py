from sqlalchemy.orm.attributes import flag_modified

from infrastructure.database import SessionLocal
from infrastructure.models.zone_model import ZoneModel

# JSON-колонки ZoneModel — SQLAlchemy не завжди детектує мутації,
# тому після setattr явно позначаємо їх як модифіковані.
_JSON_FIELDS = {"polygon", "time_windows", "risk_multipliers", "people_thresholds", "accumulation"}


class ZoneRepositoryImpl:

    def create(self, data):
        db = SessionLocal()
        try:
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
        finally:
            db.close()
        return zone

    def get_by_camera(self, camera_id: str):
        db = SessionLocal()
        try:
            zones = db.query(ZoneModel).filter(
                ZoneModel.camera_id == camera_id,
                ZoneModel.is_active == True,
            ).all()
        finally:
            db.close()
        return zones

    def update(self, zone_id, data):
        db = SessionLocal()
        try:
            zone = db.query(ZoneModel).filter(ZoneModel.id == zone_id).first()
            if not zone:
                return None

            updates = data.model_dump(exclude_none=True)
            for field, value in updates.items():
                if hasattr(zone, field):
                    setattr(zone, field, value)
                    # JSON-колонки не завжди маркуються dirty автоматично
                    if field in _JSON_FIELDS:
                        flag_modified(zone, field)

            db.commit()
            db.refresh(zone)
        finally:
            db.close()
        return zone

    def delete(self, zone_id):
        db = SessionLocal()
        try:
            zone = db.query(ZoneModel).filter(ZoneModel.id == zone_id).first()
            if not zone:
                return None
            camera_id = zone.camera_id
            db.delete(zone)
            db.commit()
        finally:
            db.close()
        return camera_id
