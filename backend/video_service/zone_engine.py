from shapely.geometry import Point, Polygon
from typing import List
from models import DetectionResult
from zone_models import Zone


class ZoneEngine:
    def __init__(self, zones: List[Zone]):
        self.zones = zones

    def check(self, detection: DetectionResult):
        results = []

        cx = detection.bbox.x + detection.bbox.w / 2
        cy = detection.bbox.y + detection.bbox.h / 2
        point = Point(cx, cy)

        for zone in self.zones:
            if detection.label not in zone.forbidden_classes:
                continue

            polygon = Polygon(zone.polygon)

            if polygon.contains(point):
                results.append(
                    {"zone_id": zone.id, "zone_name": zone.name, "inside": True}
                )

        return results
