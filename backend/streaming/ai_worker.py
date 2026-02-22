import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

from ai.detector import detect_frame
from ai.zone_checker import is_inside
from ai.risk_engine import calculate_risk
from application.services.zone_service import ZoneService

zone_service = ZoneService()

MAX_QUEUE_SIZE = 200
MAX_WORKERS = 4
FRAME_TIMEOUT = 5
ZONE_CACHE_TTL = 10

frame_queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

zone_cache = {}
zone_cache_time = {}

stats = {
    "processed": 0,
    "dropped": 0,
    "last_log": time.time()
}


# ENQUEUE
async def enqueue_frame(camera_id: str, frame_base64: str) -> None:
    item = {
        "camera_id": camera_id,
        "frame": frame_base64,
        "timestamp": time.time()
    }

    try:
        frame_queue.put_nowait(item)
    except asyncio.QueueFull:
        stats["dropped"] += 1
        print(f"[AI] Queue full. Dropping frame from {camera_id}")


# CACHE
async def get_cached_zones(camera_id: str):

    now = time.time()

    if (
        camera_id not in zone_cache or
        now - zone_cache_time.get(camera_id, 0) > ZONE_CACHE_TTL
    ):
        zones = await zone_service.list(camera_id)

        zone_cache[camera_id] = zones
        zone_cache_time[camera_id] = now

    return zone_cache[camera_id]


# WORKER
async def ai_worker() -> None:

    print("[AI] Worker started")
    loop = asyncio.get_running_loop()

    while True:

        item: Dict[str, Any] = await frame_queue.get()

        if time.time() - item["timestamp"] > FRAME_TIMEOUT:
            stats["dropped"] += 1
            frame_queue.task_done()
            continue

        try:

            # detect_frame sync
            detections = await loop.run_in_executor(
                executor,
                detect_frame,
                item["frame"]
            )

            stats["processed"] += 1

            # zones async
            zones = await get_cached_zones(item["camera_id"])

            zone_hits = []

            for detection in detections:
                for zone in zones:
                    if is_inside(detection["bbox"], zone.polygon):
                        zone_hits.append(zone)

            risk = calculate_risk(len(detections), zone_hits)

            print(
                f"[AI] Camera={item['camera_id']} "
                f"Zones={len(zones)} "
                f"Hits={len(zone_hits)} "
                f"Risk={risk}%"
            )

        except Exception as e:
            print(f"[AI] ERROR processing frame: {e}")

        frame_queue.task_done()
        _log_stats()


# METRICS
def _log_stats() -> None:
    now = time.time()

    if now - stats["last_log"] > 5:
        print(
            f"[AI] Stats: processed={stats['processed']} "
            f"dropped={stats['dropped']} "
            f"queue_size={frame_queue.qsize()}"
        )
        stats["last_log"] = now
