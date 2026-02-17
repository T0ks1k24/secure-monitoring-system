from fastapi import FastAPI, Body
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from pipeline import VideoPipeline
import json
import time

app = FastAPI(
    title="Secure Monitoring System",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipelines = {
    1: VideoPipeline(video_path="../video/test.mp4", camera_id=1),
    2: VideoPipeline(video_path="../video/test_2.mp4", camera_id=2),
}

# ================== HEALTH ==================
@app.get("/")
def root():
    return {"status": "backend is running"}


@app.get("/health")
def health():
    return {"ok": True}


# ================== ZONES ==================
@app.get("/zones/{camera_id}")
def get_zones(camera_id: int):
    pipeline = pipelines.get(camera_id)

    return [z.model_dump() for z in pipeline.zones]


# ================== EVENTS (SSE) ==================
@app.get("/events/stream")
def events_stream():
    def event_generator():
        for event in pipeline.events():
            payload = {
                "event": event["event"],
                "object": event["object"],
                "confidence": event["confidence"],
                "zones": event["zones"],
                "risk": pipeline.risk_level(),
            }

            yield f"data: {json.dumps(payload)}\n\n"
            time.sleep(0.05)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


# ================== RISK ==================
@app.get("/risk")
def risk():
    return {"risk": pipeline.risk_level()}


# ================== VIDEO STREAM ==================
@app.get("/video/stream/{camera_id}")
def video_stream(camera_id: int):
    pipeline = pipelines.get(camera_id)

    return StreamingResponse(
        pipeline.video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

@app.post("/zones/{camera_id}")
def add_zone(camera_id: int, zone: dict = Body(...)):
    pipeline = pipelines.get(camera_id)
    new_zone = pipeline.add_zone(zone)
    return new_zone.model_dump()
