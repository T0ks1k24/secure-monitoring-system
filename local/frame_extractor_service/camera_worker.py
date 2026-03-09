from __future__ import annotations

import asyncio
import cv2
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable

from schemas import CameraConfig, CameraStatus
from ai_client import AIClient

logger = logging.getLogger(__name__)


@dataclass
class CameraStats:
    frames_sent: int = 0
    frames_failed: int = 0


class CameraWorker:
    """
    Async worker для однієї RTSP камери.
    - Читає потік через cv2.VideoCapture (у executor, щоб не блокувати event loop)
    - Throttle по FPS
    - Відправляє кадри на AI сервіс
    - Повідомляє менеджера про зміну статусу через callback
    """

    def __init__(
        self,
        config: CameraConfig,
        ai_client: AIClient,
        global_fps: float,
        global_resize_width: int,
        global_jpeg_quality: int,
        global_reconnect_delay: int,
        on_status_change: Optional[Callable[[str, CameraStatus], Awaitable[None]]] = None,
    ):
        self.config = config
        self.ai_client = ai_client
        self.stats = CameraStats()

        # Параметри: беремо з конфіга камери або глобальні
        self.fps: float = config.fps if config.fps is not None else global_fps
        self.resize_width: int = config.resize_width if config.resize_width is not None else global_resize_width
        self.jpeg_quality: int = config.jpeg_quality if config.jpeg_quality is not None else global_jpeg_quality
        self.reconnect_delay: int = global_reconnect_delay

        self._status: CameraStatus = CameraStatus.STOPPED
        self._on_status_change = on_status_change
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    # ──────────────────────────────────────────────
    # Public interface
    # ──────────────────────────────────────────────

    @property
    def camera_id(self) -> str:
        return self.config.id

    @property
    def status(self) -> CameraStatus:
        return self._status

    def update_params(
        self,
        fps: Optional[float] = None,
        resize_width: Optional[int] = None,
        jpeg_quality: Optional[int] = None,
    ) -> None:
        """Оновлення параметрів на льоту без рестарту воркера."""
        if fps is not None:
            self.fps = fps
        if resize_width is not None:
            self.resize_width = resize_width
        if jpeg_quality is not None:
            self.jpeg_quality = jpeg_quality

    def start(self) -> None:
        """Запуск воркера як asyncio.Task."""
        if self._task is not None and not self._task.done():
            logger.warning(f"[{self.camera_id}] Already running")
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(
            self._run(), name=f"worker-{self.camera_id}"
        )
        logger.info(f"[{self.camera_id}] Worker started")

    async def stop(self) -> None:
        """Зупинка воркера та очікування завершення."""
        self._stop_event.set()
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        await self._set_status(CameraStatus.STOPPED)
        logger.info(f"[{self.camera_id}] Worker stopped")

    # ──────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────

    async def _set_status(self, new_status: CameraStatus) -> None:
        if self._status == new_status:
            return
        self._status = new_status
        if self._on_status_change is not None:
            await self._on_status_change(self.camera_id, new_status)

    async def _run(self) -> None:
        """Головний цикл: підключення → читання → throttle → відправка."""
        loop = asyncio.get_running_loop()
        cap: Optional[cv2.VideoCapture] = None
        last_send_time: float = 0.0

        try:
            while not self._stop_event.is_set():

                # ── Підключення ──────────────────────────────
                if cap is None or not cap.isOpened():
                    await self._set_status(CameraStatus.CONNECTING)
                    logger.info(f"[{self.camera_id}] Connecting to {self.config.rtsp}")

                    # VideoCapture є blocking — виносимо в executor
                    rtsp = self.config.rtsp
                    cap = await loop.run_in_executor(
                        None,
                        lambda: cv2.VideoCapture(rtsp, cv2.CAP_FFMPEG),
                    )

                    if not cap.isOpened():
                        await self._set_status(CameraStatus.ERROR)
                        logger.warning(
                            f"[{self.camera_id}] Connection failed, "
                            f"retry in {self.reconnect_delay}s"
                        )
                        cap = None
                        await asyncio.sleep(self.reconnect_delay)
                        continue

                    await self._set_status(CameraStatus.RUNNING)
                    logger.info(f"[{self.camera_id}] Connected!")

                # ── Читання кадру (blocking → executor) ──────
                ret, frame = await loop.run_in_executor(None, cap.read)

                if not ret:
                    logger.warning(f"[{self.camera_id}] Lost frame, reconnecting...")
                    cap.release()
                    cap = None
                    await self._set_status(CameraStatus.ERROR)
                    await asyncio.sleep(self.reconnect_delay)
                    continue

                # ── Throttle по FPS ───────────────────────────
                now = time.monotonic()
                frame_interval = 1.0 / self.fps
                remaining = frame_interval - (now - last_send_time)
                if remaining > 0:
                    await asyncio.sleep(remaining)
                    continue
                last_send_time = time.monotonic()

                # ── Ресайз ────────────────────────────────────
                if self.resize_width > 0:
                    h, w = frame.shape[:2]
                    if w != self.resize_width:
                        new_h = int(h * self.resize_width / w)
                        frame = cv2.resize(frame, (self.resize_width, new_h))

                # ── Відправка на AI ───────────────────────────
                result = await self.ai_client.send_frame(
                    frame, self.camera_id, self.jpeg_quality
                )
                if result is not None:
                    self.stats.frames_sent += 1
                else:
                    self.stats.frames_failed += 1

        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception(f"[{self.camera_id}] Unexpected error")
            await self._set_status(CameraStatus.ERROR)
        finally:
            if cap is not None and cap.isOpened():
                cap.release()
            self._status = CameraStatus.STOPPED
            logger.info(f"[{self.camera_id}] Worker finished")
