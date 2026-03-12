"""
Головний пайплайн обробки кадру:
  frame → YOLO → tracker → zone intersection → risk engine → RabbitMQ
"""
from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

import numpy as np

from models.detector import detector
from services.tracker import tracker_registry, Track
from services.zone_manager import zone_manager
from services.risk_engine import risk_engine
from services.rabbitmq_service import rabbitmq_service
from schemas.events import (
    DetectRequest, DetectResponse, TrackedObject, SecurityEvent, Zone
)
from config.settings import settings

logger = logging.getLogger(__name__)


class AnalyzePipeline:
    """
    Stateless клас (state зберігається в tracker_registry та zone_manager).
    Один виклик process() = один кадр однієї камери.
    """

    async def process(
        self,
        frame: np.ndarray,
        request: DetectRequest,
    ) -> DetectResponse:
        t_start = time.monotonic()
        frame_ts = request.frame_timestamp or time.time()
        camera_id = request.camera_id

        # ── Step 1: YOLO detect ───────────────────────────────────
        raw_detections = detector.detect(frame)
        # raw_detections: List[(BoundingBox, class_name, confidence)]

        # ── Step 2: Track ─────────────────────────────────────────
        tracker = tracker_registry.get(camera_id, fps=request.stream_fps)
        zones = await zone_manager.get_zones(camera_id)
        zone_ids = [z.id for z in zones]

        confirmed_tracks: List[Track] = tracker.update(raw_detections, zone_ids)

        # ── Step 3: Zone intersection ─────────────────────────────
        zone_memberships: Dict[int, List[Zone]] = {}
        for track in confirmed_tracks:
            track_zones = zone_manager.find_zones_for_object(
                zones,
                track.bbox.cx, track.bbox.cy,
                track.bbox.x1, track.bbox.y1,
                track.bbox.x2, track.bbox.y2,
                intersection_mode="feet",
            )
            zone_memberships[track.id] = track_zones

        # Оновлюємо zone events (enter/exit)
        zone_change_events = tracker.get_zone_events(
            confirmed_tracks,
            {tid: {z.id for z in zones_list}
             for tid, zones_list in zone_memberships.items()},
        )

        # ── Step 4: Risk analysis ─────────────────────────────────
        security_events = risk_engine.analyze(
            camera_id=camera_id,
            tracks=confirmed_tracks,
            zone_memberships=zone_memberships,
            frame_timestamp=frame_ts,
            fps=request.stream_fps,
        )

        # ── Step 5: Publish to RabbitMQ ───────────────────────────
        published = 0
        if security_events:
            published = await rabbitmq_service.publish_events(security_events)
            for evt in security_events:
                logger.info(
                    f"[{camera_id}] 🚨 {evt.event_type} | "
                    f"risk={evt.risk_level} | "
                    f"track={evt.track_id} | "
                    f"zone={evt.zone_name or '-'}"
                )

        # ── Step 6: Build response ────────────────────────────────
        tracked_objects = [t.to_schema() for t in confirmed_tracks]

        processing_ms = (time.monotonic() - t_start) * 1000

        return DetectResponse(
            camera_id=camera_id,
            frame_timestamp=frame_ts,
            tracked_objects=tracked_objects,
            events_published=published,
            processing_time_ms=processing_ms,
        )


pipeline = AnalyzePipeline()
