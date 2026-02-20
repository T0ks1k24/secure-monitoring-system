from fastapi import APIRouter, Depends
from application.dto.ai_event_dto import AIEventDTO
from application.services.event_service import EventService
from application.services.risk_service import RiskService
from infrastructure.repositories.event_repo_impl import EventRepositoryImpl
from infrastructure.repositories.zone_repo_impl import ZoneRepositoryImpl
from core.websocket import ws_manager


router = APIRouter(prefix="/ai", tags=["AI"])


def get_event_service():

    return EventService(
        event_repo=EventRepositoryImpl(),
        zone_repo=ZoneRepositoryImpl(),
        risk_service=RiskService()
    )


@router.post("/events")
async def receive_ai_event(
    dto: AIEventDTO,
    service: EventService = Depends(get_event_service)
):

    event = service.process_ai_event(dto)

    await ws_manager.broadcast({
        "camera_id": event.camera_id,
        "persons": event.persons,
        "zone_id": str(event.zone_id),
        "timestamp": str(event.timestamp),
        "risk": event.risk.value
    })

    return {"status": "ok"}
