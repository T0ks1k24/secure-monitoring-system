"""
CameraWorkerFactory — creates CameraWorker instances with
proper sources, processors, and sinks.

Follows the Open/Closed principle: new worker types can be added
by creating a new factory, without modifying existing code.
"""
from __future__ import annotations

import logging

from config import Settings
from schemas import CameraConfig
from core.camera_worker import CameraWorker
from core.interfaces.i_ai_client import IAIClient
from core.interfaces.i_camera_worker_factory import ICameraWorkerFactory
from core.implementations.rtsp_frame_source import RTSPFrameSource
from core.implementations.ai_client_sink import AIClientSink
from detection.motion_detector_processor import MotionDetectorProcessor

logger = logging.getLogger(__name__)


class CameraWorkerFactory(ICameraWorkerFactory):
    """Production factory: RTSP source → motion processor → AI sink."""

    def __init__(self, ai_client: IAIClient, settings: Settings) -> None:
        self._ai_client = ai_client
        self._settings = settings

    def create_worker(self, config: CameraConfig) -> CameraWorker:
        source = RTSPFrameSource(config.rtsp)
        processors = [
            MotionDetectorProcessor(
                config.motion,
                config.resize_width or self._settings.DEFAULT_RESIZE_WIDTH,
            )
        ]
        sinks = [
            AIClientSink(
                self._ai_client,
                config.jpeg_quality or self._settings.DEFAULT_JPEG_QUALITY,
            )
        ]
        return CameraWorker(
            config=config,
            source=source,
            processors=processors,
            sinks=sinks,
            global_fps=self._settings.DEFAULT_FPS,
            global_reconnect_delay=self._settings.DEFAULT_RECONNECT_DELAY,
        )
