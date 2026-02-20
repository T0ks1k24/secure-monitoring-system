from fastapi import FastAPI, WebSocket
from contextlib import asynccontextmanager

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
from core.db_waiter import wait_for_db


# ------------------------------
# Lifespan Startup
# ------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("\n🔄 Starting Server...")

    wait_for_db()

    Base.metadata.create_all(bind=engine)

    create_default_admin()

    ips = get_server_addresses()

    print("\n==============================")
    print("🚀 Server Started")
    print(f"Local IP:  http://{ips['local_ip']}:8000")

    if ips["public_ip"]:
        print(f"Public IP: http://{ips['public_ip']}:8000")

    print("==============================\n")

    yield

    print("\n🛑 Server Shutdown")


# ------------------------------
# Create FastAPI App
# ------------------------------

app = FastAPI(
    title="Security Monitoring System",
    version="1.0.0",
    lifespan=lifespan
)

# ------------------------------
# Include Routers
# ------------------------------

app.include_router(ai_router)
app.include_router(event_router)
app.include_router(zone_router)
app.include_router(server_router)
app.include_router(auth_router)


# ------------------------------
# WebSocket Endpoint
# ------------------------------

@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):

    await ws_manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()
    except:
        ws_manager.disconnect(websocket)


# ------------------------------
# Healthcheck
# ------------------------------

@app.get("/health")
def health_check():
    return {"status": "ok"}
