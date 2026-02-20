from fastapi import APIRouter, Depends
from infrastructure.repositories.event_repo_impl import EventRepositoryImpl


router = APIRouter(prefix="/events", tags=["Events"])


def get_event_repo():
    return EventRepositoryImpl()


@router.get("/")
def get_all(repo = Depends(get_event_repo)):

    events = repo.get_all()

    return [
        {
            "id": str(e.id),
            "camera_id": e.camera_id,
            "persons": e.persons,
            "zone_id": str(e.zone_id),
            "timestamp": str(e.timestamp),
            "risk": e.risk.value
        }
        for e in events
    ]
