import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from camera_manager import camera_manager
from api.routes import router
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("=== Frame Extractor Service starting ===")
    await camera_manager.startup()
    yield
    logger.info("=== Frame Extractor Service stopping ===")
    await camera_manager.shutdown()


app = FastAPI(
    title="Frame Extractor Service",
    description="Локальний сервіс захоплення кадрів з RTSP камер",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — фронтенд може стукати з будь-якого origin (у продакшні замінити на конкретний)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
    )
