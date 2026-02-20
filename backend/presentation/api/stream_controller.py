from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from application.services.ai_client import enqueue_frame

router = APIRouter()


@router.websocket("/ws/stream/{camera_id}")
async def stream_receiver(websocket: WebSocket, camera_id: str):

    await websocket.accept()

    print(f"Camera {camera_id} connected")

    try:
        while True:

            # Electron шле base64 JPEG
            frame_base64 = await websocket.receive_text()

            # Backend тільки forward у AI
            enqueue_frame(camera_id, frame_base64)

    except WebSocketDisconnect:
        print(f"Camera {camera_id} disconnected")
