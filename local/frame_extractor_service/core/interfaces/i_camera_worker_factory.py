from __future__ import annotations

from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from schemas import CameraConfig
    from core.camera_worker import CameraWorker


class ICameraWorkerFactory(Protocol):
    """Protocol for creating CameraWorker instances (Open/Closed)."""

    def create_worker(self, config: "CameraConfig") -> "CameraWorker": ...
