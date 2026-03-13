from fastapi import APIRouter
from core.server_info import get_server_addresses


router = APIRouter(prefix="/server", tags=["Server"])


@router.get("/info")
def server_info():

    return get_server_addresses()
