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
        "- `active_cameras`: count of running cameras.\n"
        "- `total_cameras`: total number of added cameras.\n"
        "- `ai_service_url`: where frames are sent for analysis.\n"
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
        active_workers=active,
        ai_service_url=settings.AI_SERVICE_URL,
        fps=settings.DEFAULT_FPS,
        resize_width=settings.DEFAULT_RESIZE_WIDTH,
        jpeg_quality=settings.DEFAULT_JPEG_QUALITY,
    )


@router.get(
    "/config",
    summary="Get current global settings",
)
async def get_config(
    manager: CameraManager = Depends(get_camera_manager),
) -> dict:
    current_settings = getattr(manager, "_settings", settings)
    return {
        "default_fps": current_settings.DEFAULT_FPS,
        "default_resize_width": current_settings.DEFAULT_RESIZE_WIDTH,
        "default_jpeg_quality": current_settings.DEFAULT_JPEG_QUALITY,
        "ai_service_url": current_settings.AI_SERVICE_URL,
        "default_reconnect_delay": current_settings.DEFAULT_RECONNECT_DELAY,
    }


@router.patch(
    "/config",
    summary="Update global settings",
    description=(
        "Allows changing service parameters on the fly.\n\n"
        "- **ai_service_url**: service will immediately start sending frames to the new address.\n"
        "- **fps**, **resize_width**, **jpeg_quality**: global defaults for new cameras."
    ),
)
async def update_config(
    body: GlobalConfigUpdate,
    manager: CameraManager = Depends(get_camera_manager),
) -> dict:
    updates = {}
    if body.ai_service_url is not None:
        updates["ai_service_url"] = body.ai_service_url
    if body.default_fps is not None:
        updates["default_fps"] = body.default_fps
    if body.default_resize_width is not None:
        updates["default_resize_width"] = body.default_resize_width
    if body.default_jpeg_quality is not None:
        updates["default_jpeg_quality"] = body.default_jpeg_quality
    if body.default_reconnect_delay is not None:
        updates["default_reconnect_delay"] = body.default_reconnect_delay

    manager.update_global_config(**updates)
    return {"status": "updated"}
