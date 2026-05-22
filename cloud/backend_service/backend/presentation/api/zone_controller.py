from fastapi import APIRouter, HTTPException
from application.services.zone_service import ZoneService
from application.dto.zone_dto import ZoneCreateDTO, ZoneUpdateDTO, ZoneResponseDTO

router = APIRouter(prefix="/api/zones", tags=["Zones"])

service = ZoneService()


@router.post("/", response_model=ZoneResponseDTO)
async def create_zone(dto: ZoneCreateDTO):
    return await service.create(dto)


@router.get("/{camera_id}", response_model=list[ZoneResponseDTO])
async def get_zones(camera_id: str):
    return await service.list(camera_id)


@router.put("/{zone_id}", response_model=ZoneResponseDTO)
async def update_zone(zone_id: int, dto: ZoneUpdateDTO):
    result = await service.update(zone_id, dto)
    if not result:
        raise HTTPException(status_code=404)
    return result


@router.delete("/{zone_id}")
async def delete_zone(zone_id: int):
    result = await service.delete(zone_id)
    if not result:
        raise HTTPException(status_code=404)
    return {"deleted": True}
