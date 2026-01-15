from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse

from pipeline import VideoPipeline
import json
import time

app = FastAPI(
    title="Secure Monitoring System",
    version="1.0.0",
)

pipeline = VideoPipeline(video_path="../video/test_2.mp4")


# ================== HEALTH ==================
@app.get("/")
def root():
    return {"status": "backend is running"}


@app.get("/health")
def health():
    return {"ok": True}


# ================== ZONES ==================
@app.get("/zones")
def get_zones():
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
@app.get("/video/stream")
def video_stream():
    return StreamingResponse(
        pipeline.video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
