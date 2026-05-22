from fastapi import APIRouter, Depends
from infrastructure.repositories.event_repo_impl import EventRepositoryImpl
from core.jwt_auth import get_current_user


router = APIRouter(prefix="/events", tags=["Events"])


def get_event_repo():
    return EventRepositoryImpl()


@router.get("/")
def get_all(repo = Depends(get_event_repo), _user = Depends(get_current_user)):

    events = repo.get_all()

    return [
        {
            "id": e.id,
            "camera_id": e.camera_id,
            "event_type": e.event_type,
            "object_class": e.object_class,
            "track_id": e.track_id,
            "confidence": e.confidence,
            "zone_id": e.zone_id,
            "zone_name": e.zone_name,
            "bbox": e.bbox,
            "metadata": e.metadata,
            "timestamp": e.timestamp.isoformat(),
            "risk": e.risk.value
        }
        for e in events
    ]
