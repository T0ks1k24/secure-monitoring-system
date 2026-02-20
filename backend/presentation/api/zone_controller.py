from fastapi import APIRouter, Depends
from application.services.zone_service import ZoneService
from application.dto.zone_dto import ZoneCreateDTO, ZoneUpdateDTO
from infrastructure.repositories.zone_repo_impl import ZoneRepositoryImpl


router = APIRouter(prefix="/zones", tags=["Zones"])


def get_zone_service():

    return ZoneService(
        zone_repo=ZoneRepositoryImpl()
    )


@router.post("/")
def create_zone(
    dto: ZoneCreateDTO,
    service: ZoneService = Depends(get_zone_service)
):

    zone = service.create_zone(dto)

    return {
        "id": str(zone.id),
        "name": zone.name,
        "coordinates": zone.coordinates,
        "max_people_allowed": zone.max_people_allowed
    }


@router.get("/")
def get_zones():

    repo = ZoneRepositoryImpl()

    zones = repo.get_all()

    return [
        {
            "id": str(z.id),
            "name": z.name,
            "coordinates": z.coordinates,
            "max_people_allowed": z.max_people_allowed
        }
        for z in zones
    ]


@router.put("/{zone_id}")
def update_zone(
    zone_id: str,
    dto: ZoneUpdateDTO,
    service: ZoneService = Depends(get_zone_service)
):

    zone = service.update_zone(zone_id, dto)

    return {
        "id": str(zone.id),
        "name": zone.name,
        "coordinates": zone.coordinates,
        "max_people_allowed": zone.max_people_allowed
    }


@router.delete("/{zone_id}")
def delete_zone(
    zone_id: str,
    service: ZoneService = Depends(get_zone_service)
):

    service.delete_zone(zone_id)

    return {"status": "deleted"}
