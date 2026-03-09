from __future__ import annotations

import asyncio
import cv2
import time
import logging
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable

from schemas import CameraConfig, CameraStatus
from ai_client import AIClient
from motion_detector import MotionDetector, MotionConfig

logger = logging.getLogger(__name__)


@dataclass
class CameraStats:
    frames_sent: int = 0
    frames_failed: int = 0
    frames_skipped: int = 0


def _schema_to_motion_config(s) -> MotionConfig:
    """Конвертує MotionConfigSchema (Pydantic) → MotionConfig (dataclass)."""
    return MotionConfig(
        enabled=s.enabled,
        min_contour_area=s.min_contour_area,
        min_total_area=s.min_total_area,
        min_solidity=s.min_solidity,
        min_consecutive_frames=s.min_consecutive_frames,
        cooldown_seconds=s.cooldown_seconds,
        blur_size=s.blur_size,
        diff_threshold=s.diff_threshold,
        dilate_iterations=s.dilate_iterations,
    )


class CameraWorker:
    def __init__(
        self,
        config: CameraConfig,
        ai_client: AIClient,
        global_fps: float,
        global_resize_width: int,
        global_jpeg_quality: int,
        global_reconnect_delay: int,
        on_status_change: Optional[Callable[[str, CameraStatus], Awaitable[None]]] = None,
    ) -> None:
        self.config = config
        self.ai_client = ai_client
        self.stats = CameraStats()

        self.fps: float = config.fps if config.fps is not None else global_fps
        self.resize_width: int = (
            config.resize_width if config.resize_width is not None else global_resize_width
        )
        self.jpeg_quality: int = (
            config.jpeg_quality if config.jpeg_quality is not None else global_jpeg_quality
        )
        self.reconnect_delay: int = global_reconnect_delay

        self._motion = MotionDetector(_schema_to_motion_config(config.motion))

        self._status: CameraStatus = CameraStatus.STOPPED
        self._on_status_change = on_status_change
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    # ──────────────────────────────────────────────
    # Public
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
        motion_schema=None,
    ) -> None:
        if fps is not None:
            self.fps = fps
        if resize_width is not None:
            self.resize_width = resize_width
        if jpeg_quality is not None:
            self.jpeg_quality = jpeg_quality
        if motion_schema is not None:
            self._motion.update_config(_schema_to_motion_config(motion_schema))

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            logger.warning(f"[{self.camera_id}] Already running")
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(
            self._run(), name=f"worker-{self.camera_id}"
        )
        logger.info(f"[{self.camera_id}] Worker started")

    async def stop(self) -> None:
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

    def get_motion_stats(self) -> dict:
        return self._motion.get_stats()

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
        loop = asyncio.get_running_loop()
        cap: Optional[cv2.VideoCapture] = None
        last_process_time: float = 0.0

        try:
            while not self._stop_event.is_set():

                # ── Підключення ──────────────────────────────
                if cap is None or not cap.isOpened():
                    await self._set_status(CameraStatus.CONNECTING)
                    logger.info(f"[{self.camera_id}] Connecting to {self.config.rtsp}")

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
                        self._motion.reset()
                        await asyncio.sleep(self.reconnect_delay)
                        continue

                    await self._set_status(CameraStatus.RUNNING)
                    self._motion.reset()
                    logger.info(f"[{self.camera_id}] Connected!")

                # ── Читання кадру (завжди — щоб дренувати буфер камери) ───
                ret, frame = await loop.run_in_executor(None, cap.read)

                if not ret:
                    logger.warning(f"[{self.camera_id}] Lost frame, reconnecting...")
                    cap.release()
                    cap = None
                    self._motion.reset()
                    await self._set_status(CameraStatus.ERROR)
                    await asyncio.sleep(self.reconnect_delay)
                    continue

                # FIX BUG 3: Throttle — пропускаємо обробку але НЕ перестаємо читати кадри.
                # Якщо зупинитись на sleep+continue перед cap.read, то буфер RTSP
                # накопичується і ми отримуємо застарілі кадри.
                now = time.monotonic()
                if (now - last_process_time) < (1.0 / self.fps):
                    await asyncio.sleep(0)  # yield event loop, не блокуємо
                    continue
                last_process_time = now

                # ── Ресайз ────────────────────────────────────
                if self.resize_width > 0:
                    h, w = frame.shape[:2]
                    if w != self.resize_width:
                        new_h = int(h * self.resize_width / w)
                        frame = cv2.resize(frame, (self.resize_width, new_h))

                # ── Motion detection ──────────────────────────
                if self.config.motion.enabled:
                    should_send = self._motion.detect(frame, time.monotonic())
                else:
                    should_send = True

                if not should_send:
                    self.stats.frames_skipped += 1
                    continue

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
