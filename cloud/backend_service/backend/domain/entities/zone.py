class Zone:

    def __init__(
        self,
        id: int,
        name: str,
        camera_id: str,
        polygon: list,
        zone_type: str,
        risk_weight: float,
        is_active: int = 1,
    ):
        self.id = id
        self.name = name
        self.camera_id = camera_id
        self.polygon = polygon
        self.zone_type = zone_type
        self.risk_weight = risk_weight
        self.is_active = is_active
