from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from ai import analyze_video_stream
from video_stream import generate_video
import json
import time

app = FastAPI()

person_counter = 0


@app.get("/")
def root():
    return {"status": "backend is running"}


@app.get("/events")
def events():
    def event_generator():
        global person_counter

        for event in analyze_video_stream():
            if event["event"] == "person_detected":
                person_counter += 1

            data = {
                "event": event["event"],
                "confidence": event["confidence"],
                "risk": get_risk_level(),
            }

            # SSE format
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(0.05)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def get_risk_level():
    if person_counter > 10:
        return "HIGH"
    elif person_counter > 0:
        return "MEDIUM"
    return "LOW"


@app.get("/risk")
def risk():
    return {"risk": get_risk_level()}

@app.get("/video")
def video_feed():
    return StreamingResponse(
        generate_video(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
