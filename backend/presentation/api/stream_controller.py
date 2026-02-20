from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from streaming.frame_queue import frame_queues
from streaming.yolo_worker import start_camera_worker
import base64
import numpy as np
import cv2

router = APIRouter()


@router.websocket("/ws/stream/{camera_id}")
async def stream_receiver(websocket: WebSocket, camera_id: str):

    await websocket.accept()

    print(f"Camera {camera_id} connected")

    try:
        while True:
            start_camera_worker(camera_id)
            data = await websocket.receive_text()

            jpg_bytes = base64.b64decode(data)

            np_arr = np.frombuffer(jpg_bytes, np.uint8)

            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if camera_id not in frame_queues:
                continue

            frame_queues[camera_id].put(frame)

    except WebSocketDisconnect:
        print(f"Camera {camera_id} disconnected")
