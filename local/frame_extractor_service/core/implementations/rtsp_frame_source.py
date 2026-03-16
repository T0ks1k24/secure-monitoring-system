import asyncio
import logging
from typing import Tuple, Optional

import cv2
import numpy as np

from core.interfaces.i_frame_source import IFrameSource

logger = logging.getLogger(__name__)

class RTSPFrameSource(IFrameSource):
    def __init__(self, rtsp_url: str):
        self.rtsp_url = rtsp_url
        self._cap: Optional[cv2.VideoCapture] = None

    async def connect(self) -> bool:
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
