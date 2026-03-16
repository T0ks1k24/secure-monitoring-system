from fastapi import APIRouter, Depends

from config import settings
from schemas import GlobalConfigUpdate, ServiceStatusResponse
from core.camera_manager import CameraManager
from api.deps import get_camera_manager

router = APIRouter(tags=["System"])


@router.get(
    "/health",
    summary="Health check",
    description="Check if the service is alive. Used for Docker healthcheck and monitoring.",
)
async def health() -> dict:
    return {"status": "ok"}


@router.get(
    "/status",
    response_model=ServiceStatusResponse,
    summary="Service status",
    description=(
        "Returns general information about the service:\n"
        "- `active_cameras`: count of cameras currently in `running` status.\n"
        "- `total_cameras`: total number of added cameras.\n"
        "- `ai_service_url`: where the service sends frames for analysis.\n"
        "- `fps`, `resize_width`, `jpeg_quality`: current global defaults."
    ),
)
async def get_status(
    manager: CameraManager = Depends(get_camera_manager),
) -> ServiceStatusResponse:
    cameras = manager.get_all()
    active = sum(1 for c in cameras if c.status == "running")
    return ServiceStatusResponse(
        running=True,
        total_cameras=len(cameras),
        active_cameras=active,
        ai_service_url=settings.AI_SERVICE_URL,
        fps=settings.DEFAULT_FPS,
        resize_width=settings.DEFAULT_RESIZE_WIDTH,
        jpeg_quality=settings.DEFAULT_JPEG_QUALITY,
    )


@router.patch(
    "/config",
    summary="Update global settings",
    description=(
        "Allows changing service parameters on the fly.\n\n"
        "- **ai_service_url**: if changed, the service will immediately start sending frames to the new address.\n"
        "- **fps**, **resize_width**, **jpeg_quality**: these values will be automatically applied when adding new cameras if no specific parameters are provided for them."
    ),
)
async def update_config(
    body: GlobalConfigUpdate,
    manager: CameraManager = Depends(get_camera_manager),
) -> dict:
    manager.update_global_config(
        ai_service_url=body.ai_service_url,
        default_fps=body.fps,
        default_resize_width=body.resize_width,
        default_jpeg_quality=body.jpeg_quality,
        default_reconnect_delay=body.default_reconnect_delay,
    )
    return {"status": "updated"}
