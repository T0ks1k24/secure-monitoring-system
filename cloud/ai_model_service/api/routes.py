"""
FastAPI роути AI сервісу.
"""
from __future__ import annotations

import time
import logging
from io import BytesIO
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from config.settings import settings
from models.detector import detector
from services.pipeline import pipeline
from services.zone_manager import zone_manager
from services.tracker import tracker_registry
from services.rabbitmq_service import rabbitmq_service
from schemas.events import (
    DetectRequest, DetectResponse, ServiceStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter()
_start_time = time.monotonic()


# ── Health / Status ───────────────────────────────────────────────────────────

@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "model_loaded": detector.is_loaded}


@router.get("/status", response_model=ServiceStatus)
async def get_status() -> ServiceStatus:
    return ServiceStatus(
        running=True,
        model_loaded=detector.is_loaded,
        model_path=settings.MODEL_PATH,
        device=settings.DEVICE,
        active_trackers=tracker_registry.count,
        total_zones_cached=zone_manager.total_cached_zones,
        rabbitmq_connected=rabbitmq_service.is_connected,
        uptime_seconds=time.monotonic() - _start_time,
    )


# ── Main detect endpoint ──────────────────────────────────────────────────────

@router.post(
    "/detect",
    response_model=DetectResponse,
    summary="Аналіз кадру",
    description=(
        "Приймає JPEG кадр, запускає YOLO + трекер + зональний аналіз + "
        "risk engine. Публікує SecurityEvent в RabbitMQ."
    ),
)
async def detect(
    image: UploadFile = File(..., description="JPEG кадр"),
    camera_id: str = Form(..., description="ID камери"),
    stream_fps: float = Form(default=10.0, description="FPS потоку"),
    frame_timestamp: Optional[float] = Form(
        default=None, description="Unix timestamp кадру"
    ),
) -> DetectResponse:
    if not detector.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded",
        )

    # Читаємо і декодуємо кадр
    raw = await image.read()
    buf = np.frombuffer(raw, dtype=np.uint8)
    frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to decode image",
        )

    req = DetectRequest(
        camera_id=camera_id,
        frame_timestamp=frame_timestamp,
        stream_fps=stream_fps,
    )

    return await pipeline.process(frame, req)


# ── Settings (hot-reload без рестарту) ────────────────────────────────────────

@router.patch(
    "/settings",
    summary="Оновити налаштування AI на льоту",
    description=(
        "Зміна confidence, device, tracker params тощо. "
        "Не потребує рестарту сервісу."
    ),
)
async def update_settings(
    detection_confidence: Optional[float] = None,
    detection_iou: Optional[float] = None,
    max_detections: Optional[int] = None,
    tracker_max_age_seconds: Optional[float] = None,
    tracker_min_hits: Optional[int] = None,
    zone_cache_ttl: Optional[float] = None,
    trajectory_history_frames: Optional[int] = None,
) -> dict:
    settings.update(
        DETECTION_CONFIDENCE=detection_confidence,
        DETECTION_IOU=detection_iou,
        MAX_DETECTIONS=max_detections,
        TRACKER_MAX_AGE_SECONDS=tracker_max_age_seconds,
        TRACKER_MIN_HITS=tracker_min_hits,
        ZONE_CACHE_TTL=zone_cache_ttl,
        TRAJECTORY_HISTORY_FRAMES=trajectory_history_frames,
    )
    return {
        "status": "updated",
        "current": {
            "detection_confidence": settings.DETECTION_CONFIDENCE,
            "detection_iou": settings.DETECTION_IOU,
            "max_detections": settings.MAX_DETECTIONS,
            "tracker_max_age_seconds": settings.TRACKER_MAX_AGE_SECONDS,
            "tracker_min_hits": settings.TRACKER_MIN_HITS,
            "zone_cache_ttl": settings.ZONE_CACHE_TTL,
        },
    }


# ── Debug ─────────────────────────────────────────────────────────────────────

@router.delete(
    "/trackers/{camera_id}",
    summary="Скинути трекер камери",
    description="Видаляє всі активні треки для камери.",
)
async def reset_tracker(camera_id: str) -> dict:
    tracker_registry.remove(camera_id)
    return {"status": "reset", "camera_id": camera_id}
