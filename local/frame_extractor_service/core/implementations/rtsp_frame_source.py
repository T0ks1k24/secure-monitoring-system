import asyncio
import logging
import os
from typing import Tuple, Optional
from urllib.parse import urlparse, urlunparse

import cv2
import numpy as np

from core.interfaces.i_frame_source import IFrameSource

logger = logging.getLogger(__name__)

class RTSPFrameSource(IFrameSource):
    def __init__(self, rtsp_url: str):
        self.rtsp_url = rtsp_url
        self._cap: Optional[cv2.VideoCapture] = None

    @staticmethod
    def _normalize_rtsp_url(url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme.lower() != "rtsp" or not parsed.hostname:
            return url
        if parsed.hostname not in {"localhost", "127.0.0.1"}:
            return url

        target_host = os.getenv("RTSP_LOCALHOST_REWRITE_HOST", "mediamtx")
        user_info = ""
        if parsed.username:
            user_info = parsed.username
            if parsed.password:
                user_info += f":{parsed.password}"
            user_info += "@"

        port_part = f":{parsed.port}" if parsed.port else ""
        normalized = parsed._replace(netloc=f"{user_info}{target_host}{port_part}")
        return urlunparse(normalized)

    async def connect(self) -> bool:
        effective_url = self._normalize_rtsp_url(self.rtsp_url)
        if effective_url != self.rtsp_url:
            logger.warning("RTSP rewritten for container networking: %s -> %s", self.rtsp_url, effective_url)
            self.rtsp_url = effective_url

        loop = asyncio.get_running_loop()
        self._cap = await loop.run_in_executor(
            None, lambda: cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        )
        return self._cap is not None and self._cap.isOpened()

    async def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self._cap is None or not self._cap.isOpened():
            return False, None

        loop = asyncio.get_running_loop()
        ret, frame = await loop.run_in_executor(None, self._cap.read)
        return ret, frame

    async def release(self) -> None:
        if self._cap is not None and self._cap.isOpened():
            self._cap.release()
            self._cap = None
