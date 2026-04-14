import logging
import numpy as np

from core.interfaces.i_frame_sink import IFrameSink
from core.ai_client import AIClient

logger = logging.getLogger(__name__)

class AIClientSink(IFrameSink):
    def __init__(self, ai_client: AIClient, default_jpeg_quality: int = 80):
        self.ai_client = ai_client
        self.default_jpeg_quality = default_jpeg_quality

    async def send(self, frame: np.ndarray, source_id: str, quality: int) -> bool:
        """Sends frame to AI client."""
        # Quality can be overridden dynamically, but we'll use the one from config for now
        actual_quality = quality if quality is not None else self.default_jpeg_quality

        result = await self.ai_client.send_frame(
            frame=frame,
            camera_id=source_id,
            jpeg_quality=actual_quality
        )
        return result is not None

    async def aclose(self):
        """Cleanup AI client sink."""
