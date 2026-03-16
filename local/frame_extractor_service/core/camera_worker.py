"""
CameraWorker — reads frames from a source, processes them through a
pipeline, and sends results to sinks.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Awaitable, Dict, List, Optional

from schemas import CameraConfig, CameraStatus, MotionConfig
from core.interfaces.i_frame_source import IFrameSource
from core.interfaces.i_frame_processor import IFrameProcessor
from core.interfaces.i_frame_sink import IFrameSink
from core.camera_stats import CameraStats

logger = logging.getLogger(__name__)


class CameraWorker:
    """Worker that continuously reads frames and sends them through a pipeline."""

    # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        config: CameraConfig,
        source: IFrameSource,
        processors: List[IFrameProcessor],
        sinks: List[IFrameSink],
        global_fps: float,
        global_reconnect_delay: int,
        on_status_change: Optional[
            Callable[[str, CameraStatus], Awaitable[None]]
        ] = None,
    ) -> None:
        # pylint: disable=too-many-arguments
        self.config = config
        self.source = source
        self.processors = processors
        self.sinks = sinks
        self.stats = CameraStats()

        # Custom camera settings take precedence over global settings
        self.fps: float = config.fps if config.fps is not None else global_fps
        self.reconnect_delay = global_reconnect_delay

        self._status: CameraStatus = CameraStatus.STOPPED
        self._on_status_change = on_status_change
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    # Properties

    @property
    def camera_id(self) -> str:
        return self.config.id

    @property
    def status(self) -> CameraStatus:
        return self._status

    # Public API

    def get_processor_stats(self) -> Dict[str, Any]:
        """Collect stats from the first processor that provides them."""
        for proc in self.processors:
            return proc.get_stats()
        return {}

    def update_params(
        self,
        fps: Optional[float] = None,
        resize_width: Optional[int] = None,
        jpeg_quality: Optional[int] = None,
        motion: Optional[MotionConfig] = None,
    ) -> None:
        if fps is not None:
            self.fps = fps
        if jpeg_quality is not None:
            self.config.jpeg_quality = jpeg_quality
        # Propagate to all processors
        if resize_width is not None or motion is not None:
            for proc in self.processors:
                proc.update_config(resize_width=resize_width, motion=motion)

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            logger.warning("[%s] Already running", self.camera_id)
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(
            self._run(), name=f"worker-{self.camera_id}"
        )
        logger.info("[%s] Worker started", self.camera_id)

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
        logger.info("[%s] Worker stopped", self.camera_id)

    # Internal

    async def _set_status(self, new_status: CameraStatus) -> None:
        if self._status == new_status:
            return
        self._status = new_status
        if self._on_status_change:
            await self._on_status_change(self.camera_id, new_status)

    async def _handle_connection(self) -> bool:
        """Helper to handle connection logic."""
        if self._status in (CameraStatus.STOPPED, CameraStatus.ERROR):
            await self._set_status(CameraStatus.CONNECTING)

            connected = await self.source.connect()
            if not connected:
                await self._set_status(CameraStatus.ERROR)
                logger.warning(
                    "[%s] Cannot connect, retry in %ds",
                    self.camera_id,
                    self.reconnect_delay,
                )
                await asyncio.sleep(self.reconnect_delay)
                return False

            await self._set_status(CameraStatus.RUNNING)
            logger.info("[%s] Connected", self.camera_id)
        return True

    async def _process_pipeline(self, frame: Any, now: float) -> tuple[bool, Any]:
        """Helper to run frame through processors."""
        current_frame = frame
        for processor in self.processors:
            keep, processed_frame = processor.process(current_frame, now)
            if not keep:
                return False, current_frame
            if processed_frame is not None:
                current_frame = processed_frame
        return True, current_frame

    async def _send_to_sinks(self, frame: Any) -> bool:
        """Helper to send frame to all sinks."""
        sink_success = True
        for sink in self.sinks:
            success = await sink.send(
                frame,
                self.camera_id,
                self.config.jpeg_quality or 80,
            )
            if not success:
                sink_success = False
        return sink_success

    async def _run(self) -> None:
        last_process_time: float = 0.0

        try:
            while not self._stop_event.is_set():
                if not await self._handle_connection():
                    continue

                # Read frame
                ret, frame = await self.source.read()

                if not ret or frame is None:
                    logger.warning(
                        "[%s] Lost frame, reconnecting...", self.camera_id
                    )
                    await self.source.release()
                    await self._set_status(CameraStatus.ERROR)
                    await asyncio.sleep(self.reconnect_delay)
                    continue

                # Throttle
                now = time.monotonic()
                if (now - last_process_time) < (1.0 / self.fps):
                    await asyncio.sleep(0)
                    continue
                last_process_time = now

                # Processing
                keep, processed_frame = await self._process_pipeline(frame, now)
                if not keep:
                    self.stats.frames_skipped += 1
                    continue

                # Sinks
                if await self._send_to_sinks(processed_frame):
                    self.stats.frames_sent += 1
                else:
                    self.stats.frames_failed += 1

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("[%s] Unexpected error in worker: %s", self.camera_id, e)
            await self._set_status(CameraStatus.ERROR)
            raise e
        finally:
            await self.source.release()
            for sink in self.sinks:
                await sink.close()
            self._status = CameraStatus.STOPPED
            logger.info("[%s] Worker finished", self.camera_id)
