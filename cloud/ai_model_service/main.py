"""
AI Service — FastAPI застосунок.

Запуск:
  python main.py
  або: uvicorn main:app --host 0.0.0.0 --port 5000
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from models.detector import detector
from services.zone_manager import zone_manager
from services.rabbitmq_service import rabbitmq_service
from api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("=== AI Service starting ===")

    # 1. Завантажуємо YOLO
    detector.load()

    # 2. Запускаємо Zone Manager (HTTP клієнт)
    await zone_manager.startup()

    # 3. Підключаємось до RabbitMQ
    #    Встановлюємо callback: при zone update → інвалідуємо кеш
    rabbitmq_service.set_zone_update_callback(zone_manager.invalidate)
    await rabbitmq_service.connect()

    logger.info("=== AI Service ready ===")
    yield

    # Graceful shutdown
    logger.info("=== AI Service shutting down ===")
    await rabbitmq_service.disconnect()
    await zone_manager.shutdown()
    logger.info("=== AI Service stopped ===")


app = FastAPI(
    title="AI Service",
    description=(
        "Відеоаналітика з YOLO + трекінг + зонові правила + risk engine.\n\n"
        "## Потік даних\n"
        "1. `POST /detect` — приймає JPEG кадр від Frame Extractor\n"
        "2. YOLO детектує об'єкти\n"
        "3. Трекер присвоює track_id та будує траєкторію\n"
        "4. Zone Manager завантажує зони з Backend (з кешуванням)\n"
        "5. Risk Engine аналізує порушення правил\n"
        "6. SecurityEvent публікується в RabbitMQ → DB, Alerts, Frontend\n\n"
        "## Оновлення зон\n"
        "При зміні зон на фронтенді — Backend публікує `zones.updated.{camera_id}` "
        "в RabbitMQ. AI сервіс отримує і миттєво інвалідує кеш."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

Path(settings.FRAME_STORAGE_PATH).mkdir(parents=True, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
app.mount("/evidence", StaticFiles(directory=settings.FRAME_STORAGE_PATH), name="evidence")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
    )
