from infrastructure.repositories.zone_repo_impl import ZoneRepositoryImpl

zone_repo = ZoneRepositoryImpl()


class ZoneService:

    async def create(self, data):
        return zone_repo.create(data)

    async def list(self, camera_id: str):
        return zone_repo.get_by_camera(camera_id)

    async def update(self, zone_id: int, data):
        return zone_repo.update(zone_id, data)

    async def delete(self, zone_id: int):
        return zone_repo.delete(zone_id)
