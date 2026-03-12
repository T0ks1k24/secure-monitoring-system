from fastapi import Request

from core.camera_manager import CameraManager


def get_camera_manager(request: Request) -> CameraManager:
    """Dependency: extract the CameraManager from app.state."""
    return request.app.state.camera_manager
