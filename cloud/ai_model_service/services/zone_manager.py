"""
Zone Manager - zone cache with automatic refresh.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from config.settings import settings
from schemas.events import Zone

logger = logging.getLogger(__name__)

ZONE_TYPE_MAP = {
    "danger": "restricted",
    "warning": "perimeter",
    "safe": "safe_zone",
}


def point_in_polygon(px: float, py: float, polygon: List[List[float]]) -> bool:
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        intersects = ((yi > py) != (yj > py)) and (
            px < (xj - xi) * (py - yi) / (yj - yi) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def bbox_intersects_polygon(
    bbox_cx: float,
    bbox_cy: float,
    bbox_x1: float,
    bbox_y1: float,
    bbox_x2: float,
    bbox_y2: float,
    polygon: List[List[float]],
    mode: str = "centroid",
) -> bool:
    if mode == "centroid":
        return point_in_polygon(bbox_cx, bbox_cy, polygon)
    if mode == "feet":
        return point_in_polygon(bbox_cx, bbox_y2, polygon)
    if mode == "corners":
        points = [
            (bbox_cx, bbox_cy),
            (bbox_x1, bbox_y1),
            (bbox_x2, bbox_y1),
            (bbox_x1, bbox_y2),
            (bbox_x2, bbox_y2),
        ]
        return any(point_in_polygon(x, y, polygon) for x, y in points)
    return False


class ZoneCacheEntry:
    def __init__(self, zones: List[Zone]) -> None:
        self.zones = zones
        self.loaded_at = time.monotonic()

    def is_expired(self) -> bool:
        return (time.monotonic() - self.loaded_at) > settings.ZONE_CACHE_TTL


class ZoneManager:
    def __init__(self) -> None:
        self._cache: Dict[str, ZoneCacheEntry] = {}
        self._loading: Dict[str, asyncio.Lock] = {}
        self._http_client: Optional[httpx.AsyncClient] = None

    async def startup(self) -> None:
        self._http_client = httpx.AsyncClient(
            base_url=settings.BACKEND_API_URL,
            timeout=5.0,
        )
        logger.info("ZoneManager started")

    async def shutdown(self) -> None:
        if self._http_client:
            await self._http_client.aclose()

    async def get_zones(self, camera_id: str) -> List[Zone]:
        entry = self._cache.get(camera_id)
        if entry is None or entry.is_expired():
            await self._reload(camera_id)
        return self._cache.get(camera_id, ZoneCacheEntry([])).zones

    def invalidate(self, camera_id: str) -> None:
        if camera_id in self._cache:
            del self._cache[camera_id]
            logger.info("Zone cache invalidated for camera: %s", camera_id)

    def invalidate_all(self) -> None:
        self._cache.clear()
        logger.info("All zone caches cleared")

    @property
    def total_cached_zones(self) -> int:
        return sum(len(entry.zones) for entry in self._cache.values())

    def find_zones_for_object(
        self,
        zones: List[Zone],
        bbox_cx: float,
        bbox_cy: float,
        bbox_x1: float,
        bbox_y1: float,
        bbox_x2: float,
        bbox_y2: float,
        intersection_mode: str = "feet",
    ) -> List[Zone]:
        result = []
        for zone in zones:
            if not zone.enabled:
                continue
            if bbox_intersects_polygon(
                bbox_cx,
                bbox_cy,
                bbox_x1,
                bbox_y1,
                bbox_x2,
                bbox_y2,
                zone.polygon,
                mode=intersection_mode,
            ):
                result.append(zone)
        return result

    async def _reload(self, camera_id: str) -> None:
        if camera_id not in self._loading:
            self._loading[camera_id] = asyncio.Lock()

        async with self._loading[camera_id]:
            entry = self._cache.get(camera_id)
            if entry and not entry.is_expired():
                return

            zones = await self._fetch_from_backend(camera_id)
            self._cache[camera_id] = ZoneCacheEntry(zones)
            logger.info("Loaded %d zones for camera: %s", len(zones), camera_id)

    async def _fetch_from_backend(self, camera_id: str) -> List[Zone]:
        if self._http_client is None:
            return []

        endpoints = (
            f"/zones/{camera_id}",
            f"/api/zones/{camera_id}",
        )
        last_error: Exception | None = None

        try:
            zone_payloads: list[dict[str, Any]] = []
            for endpoint in endpoints:
                try:
                    response = await self._http_client.get(endpoint)
                    response.raise_for_status()
                    raw = response.json()
                    zone_payloads = raw if isinstance(raw, list) else raw.get("zones", [])
                    break
                except httpx.HTTPError as exc:
                    last_error = exc

            zones = [self._parse_backend_zone(item) for item in zone_payloads]
            enabled_zones = [zone for zone in zones if zone.enabled]
            logger.info(
                "Fetched %d zones for camera %s from backend.",
                len(enabled_zones),
                camera_id,
            )
            return enabled_zones
        except Exception:
            logger.exception("Failed to fetch zones for %s", camera_id)

        if last_error:
            logger.error("Last backend zone fetch error for %s: %s", camera_id, last_error)

        old = self._cache.get(camera_id)
        if old:
            logger.warning("Using stale zone cache for %s", camera_id)
            return old.zones
        return []

    def _parse_backend_zone(self, payload: dict[str, Any]) -> Zone:
        zone_type = payload.get("zone_type", "restricted")
        normalized_zone_type = ZONE_TYPE_MAP.get(zone_type, zone_type)
        enabled = payload.get("enabled", payload.get("is_active", True))

        return Zone(
            id=str(payload["id"]),
            camera_id=str(payload["camera_id"]),
            name=payload["name"],
            zone_type=normalized_zone_type,
            polygon=payload.get("polygon") or [],
            enabled=bool(enabled),
            metadata={
                "risk_weight": payload.get("risk_weight"),
                "max_people_allowed": payload.get("max_people_allowed"),
            },
        )


zone_manager = ZoneManager()
