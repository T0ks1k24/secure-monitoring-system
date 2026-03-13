from fastapi import APIRouter, HTTPException, Query

from schemas import ScanRequest, ScanResult
from service.scanner import scan_network

router = APIRouter(prefix="/scanner", tags=["🔍 Сканер камер"])


@router.get(
    "/search",
    response_model=ScanResult,
    summary="Знайти камери в мережі",
    description=(
        "Сканує підмережу і повертає список знайдених RTSP камер.\n\n"
        "### Використання\n"
        "```\n"
        "GET /api/v1/scanner/search?subnet=192.168.1.0/24\n"
        "```\n\n"
        "### Що повертає\n"
        "- IP, порт і готовий RTSP URL кожної камери\n"
        "- `suggested_id` — підстав відразу в `POST /cameras`\n"
        "- `connectable=true` якщо вдалось підключитись до потоку\n\n"
        "### Час сканування\n"
        "- `/24` (254 хости, 2 порти) → ~5–30 сек\n"
        "- `/16` (~65 000 хостів) → кілька хвилин\n\n"
        "### Наступний крок\n"
        "```json\n"
        "POST /api/v1/cameras\n"
        "{ \"id\": \"<suggested_id>\", \"rtsp\": \"<rtsp_url>\" }\n"
        "```"
    ),
)
async def search_get(
    subnet: str = Query(
        default="192.168.1.0/24",
        description="Підмережа (CIDR). Приклад: `192.168.1.0/24`",
    ),
    ports: str = Query(
        default="554,8554",
        description="Порти через кому. Приклад: `554,8554,10554`",
    ),
) -> ScanResult:
    try:
        ports_list = [int(p.strip()) for p in ports.split(",") if p.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Невірний формат портів. Приклад: 554,8554")

    if not ports_list:
        raise HTTPException(status_code=400, detail="Вкажіть хоча б один порт")

    try:
        return await scan_network(
            subnet=subnet,
            ports=ports_list,
            credentials=[
                {"user": "admin", "password": ""},
                {"user": "admin", "password": "admin"},
                {"user": "admin", "password": "12345"},
            ],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/search",
    response_model=ScanResult,
    summary="Знайти камери (з власними credentials)",
    description=(
        "POST варіант — дозволяє передати свій список credentials.\n\n"
        "Корисно якщо знаєш логін/пароль камер — сканер поверне "
        "готові RTSP URL одразу з авторизацією."
    ),
)
async def search_post(body: ScanRequest) -> ScanResult:
    try:
        return await scan_network(
            subnet=body.subnet,
            ports=body.ports,
            credentials=body.credentials,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
