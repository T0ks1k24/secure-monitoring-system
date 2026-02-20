from domain.repositories.zone_repo import ZoneRepository
from domain.entities.zone import Zone
from application.dto.zone_dto import ZoneCreateDTO, ZoneUpdateDTO


class ZoneService:

    def __init__(self, zone_repo: ZoneRepository):
        self.zone_repo = zone_repo

    def create_zone(self, dto: ZoneCreateDTO):

        zone = Zone(
            name=dto.name,
            coordinates=dto.coordinates,
            max_people_allowed=dto.max_people_allowed
        )

        self.zone_repo.save(zone)

        return zone

    def update_zone(self, zone_id, dto: ZoneUpdateDTO):

        zone = self.zone_repo.get_by_id(zone_id)

        if dto.name:
            zone.name = dto.name

        if dto.coordinates:
            zone.coordinates = dto.coordinates

        if dto.max_people_allowed:
            zone.max_people_allowed = dto.max_people_allowed

        self.zone_repo.update(zone)

        return zone

    def delete_zone(self, zone_id):

        self.zone_repo.delete(zone_id)
