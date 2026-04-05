import asyncio
import json
import time

import aio_pika
import httpx
import websockets


BACKEND_URL = "http://127.0.0.1:8000"
FRAME_EXTRACTOR_URL = "http://127.0.0.1:8100"
AI_URL = "http://127.0.0.1:5000"
RABBITMQ_URL = "amqp://guest:guest@127.0.0.1:5672/"
EVENTS_EXCHANGE = "security.events"


async def wait_http(url: str, timeout: float = 60.0) -> None:
    started = time.monotonic()
    async with httpx.AsyncClient(timeout=5.0) as client:
        while time.monotonic() - started < timeout:
            try:
                response = await client.get(url)
                if response.status_code < 500:
                    return
            except Exception:
                pass
            await asyncio.sleep(1)
    raise RuntimeError(f"Timeout waiting for {url}")


async def publish_event() -> None:
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    exchange = await channel.declare_exchange(
        EVENTS_EXCHANGE,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )

    payload = {
        "event_id": "smoke-event-1",
        "camera_id": "camera1",
        "timestamp": time.time(),
        "event_type": "zone_intrusion",
        "risk_level": "high",
        "track_id": 1,
        "object_class": "person",
        "confidence": 0.99,
        "bbox": {"x1": 0.1, "y1": 0.2, "x2": 0.3, "y2": 0.4},
        "zone_id": "1",
        "zone_name": "Smoke Zone",
        "metadata": {"source": "smoke"},
    }

    await exchange.publish(
        aio_pika.Message(
            body=json.dumps(payload).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key="events.zone_intrusion.camera1",
    )
    await connection.close()


async def main() -> None:
    await wait_http(f"{BACKEND_URL}/health")
    await wait_http(f"{AI_URL}/api/v1/health")
    await wait_http(f"{FRAME_EXTRACTOR_URL}/api/v1/system/status")

    async with httpx.AsyncClient(timeout=10.0) as client:
        zone_resp = await client.post(
            f"{BACKEND_URL}/zones/",
            json={
                "name": "Smoke Zone",
                "camera_id": "camera1",
                "polygon": [[0.1, 0.1], [0.8, 0.1], [0.8, 0.8], [0.1, 0.8]],
                "zone_type": "restricted",
                "risk_weight": 50,
                "is_active": True,
                "max_people_allowed": 0,
            },
        )
        zone_resp.raise_for_status()

        zones_resp = await client.get(f"{BACKEND_URL}/zones/camera1")
        zones_resp.raise_for_status()
        zones = zones_resp.json()
        assert zones, "Backend did not return zones after create"

        add_camera_resp = await client.post(
            f"{FRAME_EXTRACTOR_URL}/api/v1/cameras",
            json={
                "name": "Smoke Camera",
                "rtsp": "rtsp://mediamtx:8554/camera1",
                "enabled": True,
            },
        )
        add_camera_resp.raise_for_status()

        camera = add_camera_resp.json()
        camera_id = camera["id"]

        for _ in range(10):
            status_resp = await client.get(
                f"{FRAME_EXTRACTOR_URL}/api/v1/cameras/{camera_id}"
            )
            status_resp.raise_for_status()
            status_payload = status_resp.json()
            if status_payload["status"] in {"running", "connecting"}:
                break
            await asyncio.sleep(1)
        else:
            raise RuntimeError("Frame extractor camera did not start")

        async with websockets.connect("ws://127.0.0.1:8000/ws/events") as websocket:
            await publish_event()
            ws_payload = json.loads(await asyncio.wait_for(websocket.recv(), timeout=15))
            assert ws_payload["id"] == "smoke-event-1"

        events_resp = await client.get(f"{BACKEND_URL}/events/")
        events_resp.raise_for_status()
        events = events_resp.json()
        assert any(evt["id"] == "smoke-event-1" for evt in events)

    print("Smoke integration passed")


if __name__ == "__main__":
    asyncio.run(main())
