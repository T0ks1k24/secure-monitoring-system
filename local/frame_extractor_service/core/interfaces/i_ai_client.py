from typing import Protocol, Optional


class IAIClient(Protocol):
    """Protocol for the AI inference client."""

    def update_endpoint(self, endpoint: str) -> None: ...

    async def aclose(self) -> None: ...

    async def send_frame(
        self, frame, camera_id: str, jpeg_quality: int = 80
    ) -> Optional[dict]: ...
