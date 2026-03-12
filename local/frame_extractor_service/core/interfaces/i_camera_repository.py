from typing import Protocol, List

from schemas.camera_config import CameraConfig


class ICameraRepository(Protocol):
    """Protocol for persisting camera configurations."""

    def load_all(self) -> List[CameraConfig]: ...

    def save_all(self, cameras: List[CameraConfig]) -> None: ...
