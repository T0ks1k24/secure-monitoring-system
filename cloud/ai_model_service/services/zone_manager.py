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


EMPTY_CACHE_TTL = 2.0   # порожній результат — перепитуємо часто

class ZoneCacheEntry:
    def __init__(self, zones: List[Zone]) -> None:
        self.zones = zones
        self.loaded_at = time.monotonic()
        # Для порожніх списків використовуємо короткий TTL,
        # щоб швидко повторити запит після додавання зон
        self._ttl = EMPTY_CACHE_TTL if not zones else settings.ZONE_CACHE_TTL

    def is_expired(self) -> bool:
        return (time.monotonic() - self.loaded_at) > self._ttl


class ZoneManager:
    def __init__(self) -> None:
        self._cache: Dict[str, ZoneCacheEntry] = {}
        self._loading: Dict[str, asyncio.Lock] = {}
        self._http_client: Optional[httpx.AsyncClient] = None

    async def startup(self) -> None:
        self._http_client = self._make_client()
        logger.info("ZoneManager started")

    @staticmethod
    def _make_client() -> httpx.AsyncClient:
        """Створює httpx клієнт з retry=1 для відновлення після stale keep-alive."""
        return httpx.AsyncClient(
            base_url=settings.BACKEND_API_URL,
            timeout=5.0,
            transport=httpx.AsyncHTTPTransport(retries=1),
        )

    async def shutdown(self) -> None:
        if self._http_client:
            await self._http_client.aclose()

    async def get_zones(self, camera_id: str) -> List[Zone]:
        entry = self._cache.get(camera_id)
        if entry is None or entry.is_expired():
            await self._reload(camera_id)
        return self._cache.get(camera_id, ZoneCacheEntry([])).zones

    def invalidate(self, camera_id: str) -> None:
        """Інвалідує кеш для camera_id та всіх його аліасів (числовий ↔ camera{N})."""
        to_remove = {camera_id}
        if camera_id.isdigit():
            to_remove.add(f"camera{camera_id}")
        elif camera_id.startswith("camera") and camera_id[6:].isdigit():
            to_remove.add(camera_id[6:])

        removed = False
        for cid in to_remove:
            if cid in self._cache:
                del self._cache[cid]
                logger.info("Zone cache invalidated for camera: %s", cid)
                removed = True
        if not removed:
            logger.debug("Zone cache invalidate called for %s — no cached entry found", camera_id)

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

        candidate_ids = [camera_id]
        if camera_id.isdigit():
            candidate_ids.append(f"camera{camera_id}")
        elif camera_id.startswith("camera") and camera_id[6:].isdigit():
            candidate_ids.append(camera_id[6:])

        endpoints = []
        for cid in candidate_ids:
            endpoints.append(f"/api/zones/{cid}")
        last_error: Exception | None = None

        try:
            zone_payloads: list[dict[str, Any]] = []
            for endpoint in endpoints:
                try:
                    response = await self._http_client.get(endpoint)
                    response.raise_for_status()
                    raw = response.json()
                    candidate_payloads = raw if isinstance(raw, list) else raw.get("zones", [])
                    # Important: don't stop on empty 200 response, try the alias camera_id too.
                    if candidate_payloads:
                        zone_payloads = candidate_payloads
                        break
                except httpx.HTTPError as exc:
                    logger.warning("Zone fetch error [%s]: %s", endpoint, exc)
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
        enabled = payload.get("enabled", payload.get("is_active", True))

        # Для safe_zone базовий режим завжди RELAXED — люди в ній є нормою
        default_base_mode = "RELAXED" if zone_type == "safe_zone" else "STRICT"

        return Zone(
            id=str(payload["id"]),
            camera_id=str(payload["camera_id"]),
            name=payload["name"],
            zone_type=zone_type,
            polygon=payload.get("polygon") or [],
            enabled=bool(enabled),
            metadata={
                "risk_weight": payload.get("risk_weight"),
                "max_people_allowed": payload.get("max_people_allowed"),
                "time_windows": payload.get("time_windows", []),
                "base_mode": payload.get("base_mode") or default_base_mode,
                "risk_multipliers": payload.get(
                    "risk_multipliers", {"relaxed": 0.3, "strict": 1.5}
                ),
                "people_thresholds": payload.get(
                    "people_thresholds", {"medium": 2, "high": 5}
                ),
                "accumulation": payload.get(
                    "accumulation", {"decay_per_second": 1.0}
                ),
                "cooldown_seconds": payload.get("cooldown_seconds", 5),
            },
        )


zone_manager = ZoneManager()
