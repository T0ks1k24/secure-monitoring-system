from fastapi import APIRouter

from api.cameras import router as cameras_router
from api.system  import router as system_router

router = APIRouter()
router.include_router(system_router)
router.include_router(cameras_router)
