from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from streaming.ai_worker import enqueue_frame

router = APIRouter()

@router.websocket("/ws/stream/{camera_id}")
async def stream_receiver(websocket: WebSocket, camera_id: str):

    await websocket.accept()

    print(f"Camera {camera_id} connected")

    try:
        while True:
            frame_base64 = await websocket.receive_text()
            print("Frame received:", len(frame_base64))

            await enqueue_frame(camera_id, frame_base64)

    except WebSocketDisconnect:
        print(f"Camera {camera_id} disconnected")
