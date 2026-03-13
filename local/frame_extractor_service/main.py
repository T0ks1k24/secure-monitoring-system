"""
main.py — Composition Root.

All singletons and dependency wiring happens here.
No other module creates production dependencies.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from core.ai_client import AIClient
from core.camera_config_repository import CameraConfigRepository
from core.camera_worker_factory import CameraWorkerFactory
from core.camera_manager import CameraManager
from service.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _create_camera_manager() -> CameraManager:
    """Composition root: wire all production dependencies."""
    ai_client = AIClient(
        endpoint=settings.AI_SERVICE_URL,
        timeout=settings.AI_REQUEST_TIMEOUT,
    )
    repository = CameraConfigRepository(settings.CAMERAS_CONFIG_PATH)
    worker_factory = CameraWorkerFactory(ai_client=ai_client, settings=settings)
    return CameraManager(
        worker_factory=worker_factory,
        repository=repository,
        ai_client=ai_client,
        settings=settings,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("=== Frame Extractor Service starting ===")
    manager = _create_camera_manager()
    app.state.camera_manager = manager
    await manager.startup()
    yield
    logger.info("=== Frame Extractor Service stopping ===")
    await manager.shutdown()


app = FastAPI(
    title="Frame Extractor Service",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

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
