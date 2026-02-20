import uuid
from typing import List


class Zone:

    def __init__(
        self,
        name: str,
        coordinates: List[List[int]],
        max_people_allowed: int,
        id: uuid.UUID | None = None
    ):

        self.id = id or uuid.uuid4()
        self.name = name
        self.coordinates = coordinates
        self.max_people_allowed = max_people_allowed
