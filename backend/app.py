from fastapi import FastAPI
from ai import analyze_video

app = FastAPI()


@app.get("/events")
def events():
    return analyze_video()


@app.get("/risk")
def risk():
    count = len(analyze_video())
    if count > 3:
        return {"risk": "HIGH"}
    elif count > 0:
        return {"risk": "MEDIUM"}
    return {"risk": "LOW"}
