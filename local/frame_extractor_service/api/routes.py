from fastapi import APIRouter, HTTPException, status

from config import settings
from schemas import (
    CameraCreateRequest,
    CameraUpdateRequest,
    CameraStatusResponse,
    GlobalConfigUpdate,
    ServiceStatusResponse,
)
from camera_manager import camera_manager

router = APIRouter()


# ──────────────────────────────────────────────
# Service level
# ──────────────────────────────────────────────

@router.get("/health", summary="Health check")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/status", response_model=ServiceStatusResponse, summary="Статус сервісу")
async def get_service_status() -> ServiceStatusResponse:
    cameras = camera_manager.get_all_cameras()
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


@router.patch("/config", summary="Оновити глобальні налаштування")
async def update_global_config(body: GlobalConfigUpdate) -> dict:
    camera_manager.update_global_config(
        ai_service_url=body.ai_service_url,
        default_fps=body.default_fps,
        default_resize_width=body.default_resize_width,
        default_jpeg_quality=body.default_jpeg_quality,
        default_reconnect_delay=body.default_reconnect_delay,
    )
    return {"status": "updated"}


# ──────────────────────────────────────────────
# Cameras CRUD
# ──────────────────────────────────────────────

@router.get("/cameras", response_model=list[CameraStatusResponse], summary="Список камер")
async def list_cameras() -> list[CameraStatusResponse]:
    return camera_manager.get_all_cameras()


@router.get(
    "/cameras/{camera_id}",
    response_model=CameraStatusResponse,
    summary="Отримати камеру",
)
async def get_camera(camera_id: str) -> CameraStatusResponse:
    try:
        return camera_manager.get_camera(camera_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/cameras",
    response_model=CameraStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Додати камеру",
)
async def add_camera(body: CameraCreateRequest) -> CameraStatusResponse:
    try:
        return camera_manager.add_camera(body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.patch(
    "/cameras/{camera_id}",
    response_model=CameraStatusResponse,
    summary="Оновити параметри камери",
)
async def update_camera(camera_id: str, body: CameraUpdateRequest) -> CameraStatusResponse:
    try:
        return camera_manager.update_camera(camera_id, body)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/cameras/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити камеру",
)
async def remove_camera(camera_id: str) -> None:
    try:
        await camera_manager.remove_camera(camera_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ──────────────────────────────────────────────
# Camera control
# ──────────────────────────────────────────────

@router.post(
    "/cameras/{camera_id}/start",
    response_model=CameraStatusResponse,
    summary="Запустити камеру",
)
async def start_camera(camera_id: str) -> CameraStatusResponse:
    try:
        return camera_manager.start_camera(camera_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/cameras/{camera_id}/stop",
    response_model=CameraStatusResponse,
    summary="Зупинити камеру",
)
async def stop_camera(camera_id: str) -> CameraStatusResponse:
    try:
        return await camera_manager.stop_camera(camera_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
