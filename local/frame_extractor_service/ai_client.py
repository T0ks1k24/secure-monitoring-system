import httpx
import cv2
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AIClient:
    def __init__(self, endpoint: str, timeout: int = 5):
        self.endpoint = endpoint
        self.timeout = timeout

    async def send_frame(self, frame, camera_id: str, jpeg_quality: int = 80) -> Optional[dict]:
        """
        Асинхронно відправляє кадр на AI сервіс.
        Повертає відповідь або None при помилці.
        """
        success, buffer = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
        )
        if not success:
            logger.warning(f"[{camera_id}] Failed to encode frame")
            return None

        files = {"image": ("frame.jpg", buffer.tobytes(), "image/jpeg")}
        data = {"camera_id": camera_id}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint,
                    files=files,
                    data=data,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()

        except httpx.TimeoutException:
            logger.warning(f"[{camera_id}] AI service timeout")
        except httpx.HTTPStatusError as e:
            logger.error(f"[{camera_id}] AI service HTTP error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"[{camera_id}] AI service connection error: {e}")

        return None
