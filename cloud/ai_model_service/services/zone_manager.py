"""
Zone Manager — кеш зон з автоматичним оновленням.

Стратегія оновлення зон (вирішує проблему «як дізнатись про зміну»):

  1. TTL-кеш: кожні ZONE_CACHE_TTL секунд — перезавантажуємо з Backend API
  2. RabbitMQ push: Backend публікує "zones.updated.{camera_id}" → миттєве оновлення
  3. Manual invalidate: виклик invalidate(camera_id) з будь-якого місця сервісу

Це дає гарантію що зони завжди свіжі: навіть якщо RabbitMQ не доступний,
TTL забезпечує максимум ZONE_CACHE_TTL секунд staleness.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple

import httpx

from config.settings import settings
from schemas.events import Zone

logger = logging.getLogger(__name__)


# ── Polygon geometry (без shapely) ───────────────────────────────────────────

def point_in_polygon(px: float, py: float, polygon: List[List[float]]) -> bool:
    """
    Ray casting algorithm — визначає чи точка (px, py) всередині полігону.
    polygon: [[x1,y1], [x2,y2], ...] у нормалізованих координатах.
    """
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def bbox_intersects_polygon(
    bbox_cx: float, bbox_cy: float,
    bbox_x1: float, bbox_y1: float,
    bbox_x2: float, bbox_y2: float,
    polygon: List[List[float]],
    mode: str = "centroid",
) -> bool:
    """
    Перевіряє чи bbox перетинає полігон.

    mode:
      "centroid"  — тільки центр bbox (швидко, достатньо для більшості випадків)
      "corners"   — будь-який кут bbox (менше false-negatives)
      "feet"      — нижній центр bbox (зручно для людей — де стоять)
    """
    if mode == "centroid":
        return point_in_polygon(bbox_cx, bbox_cy, polygon)
    elif mode == "feet":
        # Нижня центральна точка — де стоять ноги
        return point_in_polygon(bbox_cx, bbox_y2, polygon)
    elif mode == "corners":
        points = [
            (bbox_cx, bbox_cy),
            (bbox_x1, bbox_y1),
            (bbox_x2, bbox_y1),
            (bbox_x1, bbox_y2),
            (bbox_x2, bbox_y2),
        ]
        return any(point_in_polygon(x, y, polygon) for x, y in points)
    return False


# ── Zone cache entry ──────────────────────────────────────────────────────────

class ZoneCacheEntry:
    def __init__(self, zones: List[Zone]) -> None:
        self.zones = zones
        self.loaded_at = time.monotonic()

    def is_expired(self) -> bool:
        return (time.monotonic() - self.loaded_at) > settings.ZONE_CACHE_TTL


# ── Zone Manager ──────────────────────────────────────────────────────────────

class ZoneManager:
    """
    Thread-safe кеш зон.
    Завантажує зони з Backend API, кешує по camera_id.
    Слухає RabbitMQ для миттєвого інвалідування.
    """

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

    # ── Public API ────────────────────────────────────────────────

    async def get_zones(self, camera_id: str) -> List[Zone]:
        """
        Повертає актуальні зони для камери.
        Автоматично завантажує/перезавантажує якщо кеш прострочений.
        """
        entry = self._cache.get(camera_id)
        if entry is None or entry.is_expired():
            await self._reload(camera_id)
        return self._cache.get(camera_id, ZoneCacheEntry([])).zones

    def invalidate(self, camera_id: str) -> None:
        """
        Миттєво інвалідує кеш для камери.
        Викликається з RabbitMQ consumer при отриманні zones.updated.{camera_id}.
        Наступний запит get_zones() завантажить свіжі дані.
        """
        if camera_id in self._cache:
            del self._cache[camera_id]
            logger.info(f"Zone cache invalidated for camera: {camera_id}")

    def invalidate_all(self) -> None:
        """Очищає весь кеш — для debug або при реконнекті."""
        self._cache.clear()
        logger.info("All zone caches cleared")

    @property
    def total_cached_zones(self) -> int:
        return sum(len(e.zones) for e in self._cache.values())

    # ── Geometry ──────────────────────────────────────────────────

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
        """
        Знаходить всі зони в яких перебуває об'єкт.
        Використовує 'feet' mode за замовчуванням —
        нижній центр bbox, де стоять ноги людини/колеса авто.
        """
        result = []
        for zone in zones:
            if not zone.enabled:
                continue
            if bbox_intersects_polygon(
                bbox_cx, bbox_cy,
                bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                zone.polygon,
                mode=intersection_mode,
            ):
                result.append(zone)
        return result

    # ── Internal ──────────────────────────────────────────────────

    async def _reload(self, camera_id: str) -> None:
        """Завантажує зони з Backend API. Lock на camera_id — щоб не слати дублікати."""
        if camera_id not in self._loading:
            self._loading[camera_id] = asyncio.Lock()

        async with self._loading[camera_id]:
            # Перевіряємо ще раз після lock (інший coroutine міг вже завантажити)
            entry = self._cache.get(camera_id)
            if entry and not entry.is_expired():
                return

            zones = await self._fetch_from_backend(camera_id)
            self._cache[camera_id] = ZoneCacheEntry(zones)
            logger.info(f"Loaded {len(zones)} zones for camera: {camera_id}")

    async def _fetch_from_backend(self, camera_id: str) -> List[Zone]:
        """HTTP GET /api/zones?camera_id={camera_id}"""
        if self._http_client is None:
            return []
        try:
            resp = await self._http_client.get(
                "/api/zones",
                params={"camera_id": camera_id},
            )
            resp.raise_for_status()
            data = resp.json()
            zones = [Zone(**z) for z in data.get("zones", [])]
            return [z for z in zones if z.enabled]
        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching zones for {camera_id}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} fetching zones for {camera_id}")
        except Exception:
            logger.exception(f"Failed to fetch zones for {camera_id}")
        # Повертаємо старий кеш якщо є
        old = self._cache.get(camera_id)
        if old:
            logger.warning(f"Using stale zone cache for {camera_id}")
            return old.zones
        return []


zone_manager = ZoneManager()
