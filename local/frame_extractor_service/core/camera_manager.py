from __future__ import annotations

import logging
from typing import Dict, List, Optional

from config import Settings
from schemas import (
    CameraAddRequest,
    CameraConfig,
    CameraStatusResponse,
    CameraUpdateRequest,
)
from core.camera_worker import CameraWorker
from core.interfaces.i_camera_worker_factory import ICameraWorkerFactory
from core.interfaces.i_camera_repository import ICameraRepository
from core.interfaces.i_ai_client import IAIClient

logger = logging.getLogger(__name__)


class CameraManager:
    """Central worker manager. One instance for the entire service."""

    def __init__(
        self,
        worker_factory: ICameraWorkerFactory,
        repository: ICameraRepository,
        ai_client: IAIClient,
        settings: Settings,
    ) -> None:
        self._workers: Dict[int, CameraWorker] = {}
        self._factory = worker_factory
        self._repo = repository
        self._ai_client = ai_client
        self._settings = settings

    # Lifecycle

    async def startup(self) -> None:
        """Load config and start enabled cameras."""
        cameras = self._repo.load_all()
        for cfg in cameras:
            worker = self._factory.create_worker(cfg)
            self._workers[cfg.id] = worker
            if cfg.enabled:
                worker.start()
        logger.info("CameraManager started: %d cameras loaded", len(cameras))

    async def shutdown(self) -> None:
        """Stop all workers and close the HTTP client."""
        for worker in self._workers.values():
            await worker.stop()
        await self._ai_client.aclose()
        logger.info("CameraManager stopped")

    # CRUD

    def add_camera(self, req: CameraAddRequest) -> CameraStatusResponse:
        # Create config without ID first
        cfg = CameraConfig(**req.model_dump())

        # Save to repo to get the generated ID
        new_id = self._repo.add(cfg)
        cfg.id = new_id

        # Now create and register the worker
        worker = self._factory.create_worker(cfg)
        self._workers[new_id] = worker

        if cfg.enabled:
            worker.start()

        logger.info("Camera added with ID: %s", new_id)
        return self._build_response(worker)

    def update_camera(
        self, camera_id: int, req: CameraUpdateRequest
    ) -> CameraStatusResponse:
        worker = self._get_or_raise(camera_id)
        updates = req.model_dump(exclude_none=True)

        # Update top-level camera params
        for key, val in updates.items():
            if key != "motion":
                setattr(worker.config, key, val)

        # Partial update for motion config
        if req.motion is not None:
            motion_updates = req.motion.model_dump(exclude_none=True)
            for m_key, m_val in motion_updates.items():
                setattr(worker.config.motion, m_key, m_val)

        worker.update_params(
            fps=updates.get("fps"),
            resize_width=updates.get("resize_width"),
            jpeg_quality=updates.get("jpeg_quality"),
            motion=worker.config.motion if req.motion else None,
        )
        self._repo.update(worker.config)
        logger.info("Camera updated: %s", camera_id)
        return self._build_response(worker)

    async def remove_camera(self, camera_id: int) -> None:
        worker = self._get_or_raise(camera_id)
        await worker.stop()
        del self._workers[camera_id]
        self._repo.delete(camera_id)
        logger.info("Camera removed: %s", camera_id)

    # Control

    def start_camera(self, camera_id: int) -> CameraStatusResponse:
        worker = self._get_or_raise(camera_id)
        worker.start()
        worker.config.enabled = True
        self._repo.update(worker.config)
        return self._build_response(worker)

    async def stop_camera(self, camera_id: int) -> CameraStatusResponse:
        worker = self._get_or_raise(camera_id)
        await worker.stop()
        worker.config.enabled = False
        self._repo.update(worker.config)
        return self._build_response(worker)

    # Queries

    def get_all(self) -> List[CameraStatusResponse]:
        return [self._build_response(w) for w in self._workers.values()]

    def get_one(self, camera_id: int) -> CameraStatusResponse:
        return self._build_response(self._get_or_raise(camera_id))

    # Global config

    def update_global_config(
        self,
        ai_service_url: Optional[str] = None,
        default_fps: Optional[float] = None,
        default_resize_width: Optional[int] = None,
        default_jpeg_quality: Optional[int] = None,
        default_reconnect_delay: Optional[int] = None,
    ) -> None:
        self._settings.update(
            AI_SERVICE_URL=ai_service_url,
            DEFAULT_FPS=default_fps,
            DEFAULT_RESIZE_WIDTH=default_resize_width,
            DEFAULT_JPEG_QUALITY=default_jpeg_quality,
            DEFAULT_RECONNECT_DELAY=default_reconnect_delay,
        )
        # AI service URL — applies to all workers at once
        if ai_service_url is not None:
            self._ai_client.update_endpoint(ai_service_url)

    # Internal

    def _get_or_raise(self, camera_id: int) -> CameraWorker:
        worker = self._workers.get(camera_id)
        if worker is None:
            raise KeyError(f"Camera '{camera_id}' not found")
        return worker

    def _build_response(self, worker: CameraWorker) -> CameraStatusResponse:
        stats = worker.get_processor_stats()
        cfg = worker.config

        return CameraStatusResponse(
            id=cfg.id,
            name=cfg.name,
            rtsp=cfg.rtsp,
            status=worker.status,
            fps=worker.fps,
            resize_width=cfg.resize_width or self._settings.DEFAULT_RESIZE_WIDTH,
            jpeg_quality=cfg.jpeg_quality or self._settings.DEFAULT_JPEG_QUALITY,
            frames_sent=worker.stats.frames_sent,
            frames_failed=worker.stats.frames_failed,
            frames_skipped=worker.stats.frames_skipped,
            motion_events=stats.get("total_motion_events", 0),
            motion_active=stats.get("motion_detected", False),
            enabled=cfg.enabled,
            motion=cfg.motion,
        )
