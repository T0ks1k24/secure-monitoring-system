from fastapi import FastAPI
from pydantic import BaseModel
from queue_manager import frame_queue, result_queue
from worker import inference_worker
import threading


app = FastAPI()


class FrameRequest(BaseModel):
    camera_id: str
    frame: str


@app.on_event("startup")
def start_workers():

    for _ in range(2):   # 2 GPU workers
        t = threading.Thread(
            target=inference_worker,
            daemon=True
        )
        t.start()


@app.post("/enqueue")
def enqueue(req: FrameRequest):

    frame_queue.put((req.camera_id, req.frame))

    return {"status": "queued"}


@app.get("/result")
def get_result():

    if result_queue.empty():
        return None

    camera_id, detections = result_queue.get()

    return {
        "camera_id": camera_id,
        "detections": detections
    }
