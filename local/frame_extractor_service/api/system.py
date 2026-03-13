from fastapi import APIRouter, Depends

from config import settings
from schemas import GlobalConfigUpdate, ServiceStatusResponse
from core.camera_manager import CameraManager
from api.deps import get_camera_manager

router = APIRouter(tags=["⚙️ Система"])


@router.get(
    "/health",
    summary="Health check",
    description="Перевірка що сервіс живий. Для Docker healthcheck і моніторингу.",
)
async def health() -> dict:
    return {"status": "ok"}


@router.get(
    "/status",
    response_model=ServiceStatusResponse,
    summary="Статус сервісу",
    description=(
        "Загальна інформація:\n"
        "- кількість камер і скільки активних\n"
        "- поточні глобальні налаштування\n"
        "- URL AI сервісу"
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
        global_fps=settings.DEFAULT_FPS,
        global_resize_width=settings.DEFAULT_RESIZE_WIDTH,
        global_jpeg_quality=settings.DEFAULT_JPEG_QUALITY,
    )


@router.patch(
    "/config",
    summary="Оновити глобальні налаштування",
    description=(
        "Змінює глобальні налаштування.\n\n"
        "Впливають на **нові** камери (як дефолт).\n"
        "Виняток: `ai_service_url` застосовується до **всіх** воркерів одразу."
    ),
)
async def update_config(
    body: GlobalConfigUpdate,
    manager: CameraManager = Depends(get_camera_manager),
) -> dict:
    manager.update_global_config(
        ai_service_url=body.ai_service_url,
        default_fps=body.default_fps,
        default_resize_width=body.default_resize_width,
        default_jpeg_quality=body.default_jpeg_quality,
        default_reconnect_delay=body.default_reconnect_delay,
    )
    return {"status": "updated"}
