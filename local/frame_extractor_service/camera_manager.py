from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Dict, List

from config import settings
from schemas import (
    CameraConfig,
    CameraStatus,
    CameraStatusResponse,
    CameraCreateRequest,
    CameraUpdateRequest,
)
from camera_worker import CameraWorker
from ai_client import AIClient

logger = logging.getLogger(__name__)


class CameraManager:
    """
    Центральний менеджер всіх камер.
    Керує воркерами, персистить конфіг у cameras.json.
    """

    def __init__(self) -> None:
        self._workers: Dict[str, CameraWorker] = {}
        self._ai_client = AIClient(
            endpoint=settings.AI_SERVICE_URL,
            timeout=settings.AI_REQUEST_TIMEOUT,
        )
        self._config_path = Path(settings.CAMERAS_CONFIG_PATH)

    # ──────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────

    async def startup(self) -> None:
        """Викликається при старті FastAPI: завантажує та запускає камери."""
        cameras = self._load_cameras_from_file()
        for cam_cfg in cameras:
            self._create_worker(cam_cfg)
            if cam_cfg.enabled:
                self._workers[cam_cfg.id].start()
        logger.info(f"CameraManager started: {len(cameras)} cameras loaded")

    async def shutdown(self) -> None:
        """Зупиняє всі воркери при вимкненні сервісу."""
        for worker in self._workers.values():
            await worker.stop()
        logger.info("CameraManager stopped")

    # ──────────────────────────────────────────────
    # Camera CRUD
    # ──────────────────────────────────────────────

    def add_camera(self, req: CameraCreateRequest) -> CameraStatusResponse:
        if req.id in self._workers:
            raise ValueError(f"Camera '{req.id}' already exists")

        cam_cfg = CameraConfig(**req.model_dump())
        worker = self._create_worker(cam_cfg)

        if cam_cfg.enabled:
            worker.start()

        self._save_cameras_to_file()
        logger.info(f"Camera added: {req.id}")
        return self._to_response(worker)

    def update_camera(self, camera_id: str, req: CameraUpdateRequest) -> CameraStatusResponse:
        worker = self._get_or_raise(camera_id)
        update = req.model_dump(exclude_none=True)

        # Оновлюємо поля конфігу
        for key, val in update.items():
            setattr(worker.config, key, val)

        # Оновлюємо runtime-параметри воркера без рестарту
        worker.update_params(
            fps=update.get("fps"),
            resize_width=update.get("resize_width"),
            jpeg_quality=update.get("jpeg_quality"),
        )

        self._save_cameras_to_file()
        logger.info(f"Camera updated: {camera_id}")
        return self._to_response(worker)

    async def remove_camera(self, camera_id: str) -> None:
        """Зупиняє та видаляє камеру. async бо треба await worker.stop()."""
        worker = self._get_or_raise(camera_id)
        await worker.stop()
        del self._workers[camera_id]
        self._save_cameras_to_file()
        logger.info(f"Camera removed: {camera_id}")

    # ──────────────────────────────────────────────
    # Start / Stop окремих камер
    # ──────────────────────────────────────────────

    def start_camera(self, camera_id: str) -> CameraStatusResponse:
        worker = self._get_or_raise(camera_id)
        worker.start()
        worker.config.enabled = True
        self._save_cameras_to_file()
        return self._to_response(worker)

    async def stop_camera(self, camera_id: str) -> CameraStatusResponse:
        worker = self._get_or_raise(camera_id)
        await worker.stop()
        worker.config.enabled = False
        self._save_cameras_to_file()
        return self._to_response(worker)

    # ──────────────────────────────────────────────
    # Queries
    # ──────────────────────────────────────────────

    def get_all_cameras(self) -> List[CameraStatusResponse]:
        return [self._to_response(w) for w in self._workers.values()]

    def get_camera(self, camera_id: str) -> CameraStatusResponse:
        return self._to_response(self._get_or_raise(camera_id))

    def get_snapshot(self) -> dict:
        """Повний стан сервісу — для фронтенду при першому підключенні."""
        return {
            "cameras": [c.model_dump() for c in self.get_all_cameras()],
            "config": {
                "ai_service_url": settings.AI_SERVICE_URL,
                "default_fps": settings.DEFAULT_FPS,
                "default_resize_width": settings.DEFAULT_RESIZE_WIDTH,
                "default_jpeg_quality": settings.DEFAULT_JPEG_QUALITY,
                "default_reconnect_delay": settings.DEFAULT_RECONNECT_DELAY,
            },
        }

    # ──────────────────────────────────────────────
    # Global config
    # ──────────────────────────────────────────────

    def update_global_config(
        self,
        ai_service_url: Optional[str] = None,
        default_fps: Optional[float] = None,
        default_resize_width: Optional[int] = None,
        default_jpeg_quality: Optional[int] = None,
        default_reconnect_delay: Optional[int] = None,
    ) -> None:
        # Оновлюємо settings через безпечний метод
        settings.update(
            AI_SERVICE_URL=ai_service_url,
            DEFAULT_FPS=default_fps,
            DEFAULT_RESIZE_WIDTH=default_resize_width,
            DEFAULT_JPEG_QUALITY=default_jpeg_quality,
            DEFAULT_RECONNECT_DELAY=default_reconnect_delay,
        )

        # Якщо змінився URL AI — перестворюємо клієнт і прокидаємо в усі воркери
        if ai_service_url is not None:
            self._ai_client = AIClient(
                endpoint=settings.AI_SERVICE_URL,
                timeout=settings.AI_REQUEST_TIMEOUT,
            )
            for worker in self._workers.values():
                worker.ai_client = self._ai_client

    # ──────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────

    def _create_worker(self, cam_cfg: CameraConfig) -> CameraWorker:
        worker = CameraWorker(
            config=cam_cfg,
            ai_client=self._ai_client,
            global_fps=settings.DEFAULT_FPS,
            global_resize_width=settings.DEFAULT_RESIZE_WIDTH,
            global_jpeg_quality=settings.DEFAULT_JPEG_QUALITY,
            global_reconnect_delay=settings.DEFAULT_RECONNECT_DELAY,
        )
        self._workers[cam_cfg.id] = worker
        return worker

    def _get_or_raise(self, camera_id: str) -> CameraWorker:
        worker = self._workers.get(camera_id)
        if worker is None:
            raise KeyError(f"Camera '{camera_id}' not found")
        return worker

    def _to_response(self, worker: CameraWorker) -> CameraStatusResponse:
        return CameraStatusResponse(
            id=worker.camera_id,
            name=worker.config.name,
            rtsp=worker.config.rtsp,
            status=worker.status,
            fps=worker.fps,
            resize_width=worker.resize_width,
            jpeg_quality=worker.jpeg_quality,
            frames_sent=worker.stats.frames_sent,
            frames_failed=worker.stats.frames_failed,
            enabled=worker.config.enabled,
        )

    # ──────────────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────────────

    def _load_cameras_from_file(self) -> List[CameraConfig]:
        if not self._config_path.exists():
            logger.info(f"Config file not found at '{self._config_path}', starting with empty list")
            return []
        try:
            raw = self._config_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            return [CameraConfig(**cam) for cam in data.get("cameras", [])]
        except Exception as e:
            logger.error(f"Failed to load cameras config: {e}")
            return []

    def _save_cameras_to_file(self) -> None:
        try:
            cameras_data = [w.config.model_dump() for w in self._workers.values()]
            self._config_path.write_text(
                json.dumps({"cameras": cameras_data}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"Failed to save cameras config: {e}")


# Singleton — один екземпляр на весь процес
camera_manager = CameraManager()
