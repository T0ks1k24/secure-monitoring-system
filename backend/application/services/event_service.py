from infrastructure.repositories.event_repo_impl import EventRepositoryImpl
from domain.enums.risk_enum import RiskEnum

repo = EventRepositoryImpl()


class EventService:

    async def create_event(self, camera_id, persons, risk):

        if risk < 30:
            risk_level = RiskEnum.LOW
        elif risk < 70:
            risk_level = RiskEnum.MEDIUM
        else:
            risk_level = RiskEnum.HIGH

        return repo.create(
            camera_id=camera_id,
            persons=persons,
            risk=risk_level
        )
