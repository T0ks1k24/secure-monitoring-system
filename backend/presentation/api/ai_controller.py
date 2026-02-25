from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.websocket import ws_manager as manager

router = APIRouter(prefix="/ws")


@router.websocket("/events")
async def events_socket(websocket: WebSocket):

    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
