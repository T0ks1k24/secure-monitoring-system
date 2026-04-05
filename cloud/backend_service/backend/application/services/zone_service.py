from infrastructure.repositories.zone_repo_impl import ZoneRepositoryImpl
from infrastructure.messaging.rabbitmq_client import rabbitmq_client
import asyncio

zone_repo = ZoneRepositoryImpl()


class ZoneService:

    async def create(self, data):
        result = zone_repo.create(data)
        if result:
            asyncio.create_task(rabbitmq_client.publish_zone_update(result.camera_id))
        return result

    async def list(self, camera_id: str):
        return zone_repo.get_by_camera(camera_id)

    async def update(self, zone_id: int, data):
        result = zone_repo.update(zone_id, data)
        if result:
            asyncio.create_task(rabbitmq_client.publish_zone_update(result.camera_id))
        return result

    async def delete(self, zone_id: int):
        camera_id = zone_repo.delete(zone_id)
        if camera_id:
            asyncio.create_task(rabbitmq_client.publish_zone_update(camera_id))
            return True
        return False
