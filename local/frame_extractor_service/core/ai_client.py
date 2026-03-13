from __future__ import annotations

import cv2
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AIClient:
    def __init__(self, endpoint: str, timeout: int = 5) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Returns the client. Automatically creates a new one if closed."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    def update_endpoint(self, endpoint: str) -> None:
        """Change the URL of the AI ​​service without recreating the client."""
        self.endpoint = endpoint

    async def aclose(self) -> None:
        """Graceful shutdown — call when the service stops."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def send_frame(
        self,
        frame,
        camera_id: str,
        jpeg_quality: int = 80,
    ) -> Optional[dict]:
        """Encodes a frame to JPEG and sends it to the AI ​​endpoint. Returns JSON or None."""
        success, buffer = cv2.imencode(
            ".jpg", frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality],
        )
        if not success:
            logger.warning("[%s] Failed to encode frame", camera_id)
            return None

        try:
            response = await self._get_client().post(
                self.endpoint,
                files={"image": ("frame.jpg", buffer.tobytes(), "image/jpeg")},
                data={"camera_id": camera_id},
            )
            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            logger.warning("[%s] AI service timeout", camera_id)
        except httpx.HTTPStatusError as exc:
            logger.error("[%s] AI service HTTP %d", camera_id, exc.response.status_code)
        except httpx.RequestError as exc:
            logger.error("[%s] AI service connection error: %s", camera_id, exc)

        return None
