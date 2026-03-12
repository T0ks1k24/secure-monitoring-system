from fastapi import APIRouter, Depends, HTTPException, status

from schemas import (
    CameraAddRequest,
    CameraUpdateRequest,
    CameraStatusResponse,
)
from core.camera_manager import CameraManager
from api.deps import get_camera_manager

router = APIRouter(prefix="/cameras", tags=["📷 Камери"])


@router.get(
    "",
    response_model=list[CameraStatusResponse],
    summary="Список всіх камер",
    description=(
        "Повертає всі камери з поточним статусом і статистикою.\n\n"
        "**Статуси:**\n"
        "- `running` — підключена, захоплює кадри\n"
        "- `connecting` — намагається підключитись\n"
        "- `stopped` — зупинена вручну\n"
        "- `error` — втрачено з'єднання, чекає реконнект"
    ),
)
async def list_cameras(
    manager: CameraManager = Depends(get_camera_manager),
) -> list[CameraStatusResponse]:
    return manager.get_all()


@router.get(
    "/{camera_id}",
    response_model=CameraStatusResponse,
    summary="Статус камери",
    responses={404: {"description": "Камера не знайдена"}},
)
async def get_camera(
    camera_id: str,
    manager: CameraManager = Depends(get_camera_manager),
) -> CameraStatusResponse:
    try:
        return manager.get_one(camera_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "",
    response_model=CameraStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Додати камеру",
    description=(
        "Додає нову камеру і за замовчуванням одразу запускає підключення.\n\n"
        "### Мінімальний запит\n"
        "```json\n"
        '{ "id": "entrance", "rtsp": "rtsp://192.168.1.100:554/stream" }\n'
        "```\n\n"
        "Не знаєш URL? → `GET /api/v1/scanner/search?subnet=192.168.1.0/24`"
    ),
    responses={409: {"description": "Камера з таким ID вже існує"}},
)
async def add_camera(
    body: CameraAddRequest,
    manager: CameraManager = Depends(get_camera_manager),
) -> CameraStatusResponse:
    try:
        return manager.add_camera(body)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.patch(
    "/{camera_id}",
    response_model=CameraStatusResponse,
    summary="Оновити параметри камери",
    description=(
        "Передавай тільки ті поля які хочеш змінити.\n\n"
        "`fps`, `resize_width`, `jpeg_quality` — застосовуються одразу без перезапуску.\n\n"
        "Зміна `rtsp` вимагає `/stop` + `/start`."
    ),
    responses={404: {"description": "Камера не знайдена"}},
)
async def update_camera(
    camera_id: str,
    body: CameraUpdateRequest,
    manager: CameraManager = Depends(get_camera_manager),
) -> CameraStatusResponse:
    try:
        return manager.update_camera(camera_id, body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити камеру",
    responses={404: {"description": "Камера не знайдена"}},
)
async def remove_camera(
    camera_id: str,
    manager: CameraManager = Depends(get_camera_manager),
) -> None:
    try:
        await manager.remove_camera(camera_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/{camera_id}/start",
    response_model=CameraStatusResponse,
    summary="Запустити камеру",
    responses={404: {"description": "Камера не знайдена"}},
)
async def start_camera(
    camera_id: str,
    manager: CameraManager = Depends(get_camera_manager),
) -> CameraStatusResponse:
    try:
        return manager.start_camera(camera_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/{camera_id}/stop",
    response_model=CameraStatusResponse,
    summary="Зупинити камеру",
    responses={404: {"description": "Камера не знайдена"}},
)
async def stop_camera(
    camera_id: str,
    manager: CameraManager = Depends(get_camera_manager),
) -> CameraStatusResponse:
    try:
        return await manager.stop_camera(camera_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
