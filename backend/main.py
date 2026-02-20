from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import socket

from infrastructure.database import Base, engine

# Import models
from infrastructure.models.user_model import UserModel
from infrastructure.models.zone_model import ZoneModel
from infrastructure.models.event_model import EventModel

# Controllers
from presentation.api.auth_controller import router as auth_router
from presentation.api.ai_controller import router as ai_router
from presentation.api.event_controller import router as event_router
from presentation.api.zone_controller import router as zone_router
from presentation.api.server_controller import router as server_router

# WebSocket
from core.websocket import ws_manager

# Startup services
from core.server_info import get_server_addresses
from core.startup import create_default_admin


# GLOBAL READY FLAG
app_ready = False


# LIFESPAN STARTUP
@asynccontextmanager
async def lifespan(app: FastAPI):

    global app_ready

    print("\nStarting Server...")

    Base.metadata.create_all(bind=engine)
    print("Tables created!")

    create_default_admin()
    print("Default admin checked!")

    try:
        ips = get_server_addresses()
    except:
        ips = {
            "local_ip": socket.gethostbyname(socket.gethostname()),
            "public_ip": None
        }

    app_ready = True

    print("\n==============================")
    print("Server Started")
    print(f"Local:  http://localhost:8000")
    print(f"Docker: http://{ips['local_ip']}:8000")

    if ips["public_ip"]:
        print(f"Public: http://{ips['public_ip']}:8000")

    print("==============================\n")

    yield

    print("\nServer Shutdown")


# CREATE FASTAPI APP
app = FastAPI(
    title="Security Monitoring System",
    version="1.0.0",
    lifespan=lifespan
)


# INCLUDE ROUTERS
app.include_router(ai_router)
app.include_router(event_router)
app.include_router(zone_router)
app.include_router(server_router)
app.include_router(auth_router)


@app.get("/")
def root():
    return {
        "service": "Security Monitoring System",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready"
    }


# HEALTHCHECK (ALIVE)
@app.get("/health")
def health_check():
    return {"status": "ok"}


# READY
@app.get("/ready")
def ready():

    if app_ready:
        return {"status": "ready"}

    return JSONResponse(
        status_code=503,
        content={"status": "starting"}
    )


# WEBSOCKET
@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):

    await ws_manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()
    except:
        ws_manager.disconnect(websocket)
