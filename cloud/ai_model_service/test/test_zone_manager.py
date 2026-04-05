import pytest
import time
import asyncio
from unittest.mock import AsyncMock, MagicMock

from schemas.events import ZoneType
from config.settings import settings
from services.zone_manager import (
    point_in_polygon,
    bbox_intersects_polygon,
    ZoneCacheEntry,
    ZoneManager,
)

# ── Geometry tests ────────────────────────────────────────────────────────────

def test_point_in_polygon():
    poly = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    assert point_in_polygon(0.5, 0.5, poly) is True
    assert point_in_polygon(1.5, 0.5, poly) is False
    assert point_in_polygon(0.5, 1.5, poly) is False
    assert point_in_polygon(-0.1, -0.1, poly) is False

def test_bbox_intersects_polygon_centroid():
    poly = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    # Center is at 0.5, 0.5 (inside)
    assert bbox_intersects_polygon(0.5, 0.5, 0.4, 0.4, 0.6, 0.6, poly, mode="centroid") is True
    # Center is at 1.5, 0.5 (outside)
    assert bbox_intersects_polygon(1.5, 0.5, 1.4, 0.4, 1.6, 0.6, poly, mode="centroid") is False

def test_bbox_intersects_polygon_feet():
    poly = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    # Feet (bottom center) at (0.5, 0.9) - inside
    assert bbox_intersects_polygon(0.5, 0.5, 0.3, 0.1, 0.7, 0.9, poly, mode="feet") is True
    # Feet at (0.5, 1.1) - outside polygon
    assert bbox_intersects_polygon(0.5, 0.7, 0.3, 0.3, 0.7, 1.1, poly, mode="feet") is False

def test_bbox_intersects_polygon_corners():
    poly = [[0.5, 0.5], [1.0, 0.5], [1.0, 1.0], [0.5, 1.0]]
    # Center outside, but bottom-right corner (0.6, 0.6) is inside
    assert bbox_intersects_polygon(0.3, 0.3, 0.0, 0.0, 0.6, 0.6, poly, mode="corners") is True

# ── ZoneCacheEntry tests ──────────────────────────────────────────────────────

def test_zone_cache_entry_expiration(monkeypatch):
    entry = ZoneCacheEntry([])
    assert entry.is_expired() is False
    
    # Fast-forward time
    monkeypatch.setattr(time, "monotonic", lambda: entry.loaded_at + settings.ZONE_CACHE_TTL + 1)
    assert entry.is_expired() is True

# ── ZoneManager tests ─────────────────────────────────────────────────────────

@pytest.fixture
def zone_factory():
    def _create(id="z1", name="Zone 1", enabled=True):
        return {
            "id": id,
            "camera_id": "cam1",
            "name": name,
            "zone_type": "restricted",
            "polygon": [[0, 0], [1, 0], [1, 1], [0, 1]],
            "is_active": enabled,
            "risk_weight": 50,
            "max_people_allowed": 0,
        }
    return _create

@pytest.fixture
def mock_http_client():
    client = MagicMock()
    client.get = AsyncMock()
    # Mock close
    client.aclose = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_get_zones_fetch_from_backend(mock_http_client, zone_factory, monkeypatch):
    manager = ZoneManager()
    manager._http_client = mock_http_client
    
    mock_response = MagicMock()
    mock_response.json.return_value = [zone_factory()]
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    zones = await manager.get_zones("cam1")
    assert len(zones) == 1
    assert zones[0].id == "z1"
    assert zones[0].zone_type == ZoneType.RESTRICTED
    
    mock_http_client.get.assert_called_once_with("/zones/cam1")
    
    # Second call should use cache
    zones2 = await manager.get_zones("cam1")
    assert len(zones2) == 1
    assert mock_http_client.get.call_count == 1

@pytest.mark.asyncio
async def test_invalidate_zone_cache(mock_http_client, zone_factory):
    manager = ZoneManager()
    manager._http_client = mock_http_client
    
    mock_response = MagicMock()
    mock_response.json.return_value = [zone_factory()]
    mock_http_client.get.return_value = mock_response

    await manager.get_zones("cam1")
    assert manager.total_cached_zones == 1
    
    manager.invalidate("cam1")
    assert manager.total_cached_zones == 0
    
    # Next get_zones should fetch again
    await manager.get_zones("cam1")
    assert mock_http_client.get.call_count == 2

@pytest.mark.asyncio
async def test_invalidate_all_zones(mock_http_client, zone_factory):
    manager = ZoneManager()
    manager._http_client = mock_http_client
    mock_response = MagicMock()
    mock_response.json.return_value = [zone_factory()]
    mock_http_client.get.return_value = mock_response

    await manager.get_zones("cam1")
    manager.invalidate_all()
    assert manager.total_cached_zones == 0

def test_find_zones_for_object(zone_factory):
    manager = ZoneManager()
    z1 = manager._parse_backend_zone(zone_factory(id="z1", name="Inside"))
    z2 = manager._parse_backend_zone(zone_factory(id="z2", name="Disabled", enabled=False))
    
    # Object is inside z1 (0.5, 0.5)
    result = manager.find_zones_for_object([z1, z2], 0.5, 0.5, 0.4, 0.4, 0.6, 0.6, intersection_mode="centroid")
    
    assert len(result) == 1
    assert result[0].id == "z1" # z2 is skipped because disabled
