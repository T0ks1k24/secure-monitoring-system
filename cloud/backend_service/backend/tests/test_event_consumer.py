import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from infrastructure.messaging.event_consumer import EventConsumer


class _ProcessContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeMessage:
    def __init__(self, payload: dict):
        self.body = json.dumps(payload).encode()

    def process(self):
        return _ProcessContext()


@pytest.mark.asyncio
async def test_event_consumer_stores_and_broadcasts(monkeypatch):
    stored_event = SimpleNamespace(
        id="evt-1",
        camera_id="cam-1",
        event_type="zone_intrusion",
        object_class="person",
        track_id=5,
        confidence=0.88,
        timestamp=datetime(2026, 4, 1, tzinfo=timezone.utc),
        zone_id="zone-1",
        zone_name="Zone 1",
        risk=SimpleNamespace(value="HIGH"),
        bbox={"x1": 0.1, "y1": 0.2, "x2": 0.3, "y2": 0.4},
        metadata={"source": "test"},
    )
    event_service = SimpleNamespace(ingest_ai_event=lambda dto: stored_event)
    consumer = EventConsumer(event_service=event_service)
    broadcast_mock = AsyncMock()

    monkeypatch.setattr(
        "infrastructure.messaging.event_consumer.ws_manager.broadcast",
        broadcast_mock,
    )

    message = FakeMessage(
        {
            "event_id": "evt-1",
            "camera_id": "cam-1",
            "timestamp": 1710000000.0,
            "event_type": "zone_intrusion",
            "risk_level": "high",
        }
    )

    await consumer._handle_message(message)

    broadcast_mock.assert_awaited_once_with(
        {
            "id": "evt-1",
            "camera_id": "cam-1",
            "event_type": "zone_intrusion",
            "object_class": "person",
            "track_id": 5,
            "confidence": 0.88,
            "timestamp": "2026-04-01T00:00:00+00:00",
            "zone_id": "zone-1",
            "zone_name": "Zone 1",
            "risk": "HIGH",
            "bbox": {"x1": 0.1, "y1": 0.2, "x2": 0.3, "y2": 0.4},
            "metadata": {"source": "test"},
        }
    )
