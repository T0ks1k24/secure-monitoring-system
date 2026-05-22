# Secure Monitoring System

A production-grade AI-powered video surveillance platform built with a microservices architecture. The system captures live camera streams, applies real-time object detection and tracking, evaluates zone-based security rules, and pushes instant alerts to an Electron desktop application.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Services](#services)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Development](#development)
- [Project Structure](#project-structure)

---

## Overview

```
IP Cameras (RTSP)
      │
      ▼
┌─────────────┐     WebRTC/HLS      ┌──────────────────┐
│  MediaMTX   │ ──────────────────► │ Electron Frontend│
│ (RTSP Hub)  │                     │  (React + Redux) │
└──────┬──────┘                     └────────┬─────────┘
       │ RTSP                                │ HTTP (zones / cameras)
       ▼                                     ▼
┌──────────────────┐             ┌─────────────────────┐
│ Frame Extractor  │             │  Backend Service    │
│  (Python/RTSP)   │             │  (FastAPI + PG)     │
└────────┬─────────┘             └──────────┬──────────┘
         │ JPEG frames                      │ WebSocket (events)
         ▼                                  │ RabbitMQ (zones)
┌─────────────────┐   RabbitMQ             │
│   AI Service    │ ──────────────────────► │
│ YOLOv8 + Zones  │  security.events        │
└─────────────────┘                         │
                                            ▼
                                     ┌─────────────┐
                                     │  PostgreSQL  │
                                     └─────────────┘
```

---

## Key Features

| Feature | Details |
|---|---|
| **Real-time detection** | YOLOv8 object detection at configurable FPS |
| **Multi-object tracking** | Persistent track IDs across frames per camera |
| **Zone-based rules** | Restricted / Perimeter / Parking / Pedestrian / Counting zones |
| **Smart analytics** | Loitering, crowding, direction violation, abandoned object detection |
| **Live alerts** | Sub-second event delivery via WebSocket to all connected clients |
| **Evidence frames** | Annotated JPEG snapshots saved for every zone event |
| **Hot-reload zones** | Zone changes propagate to AI service without restart via RabbitMQ |
| **Role-based access** | Admin / Operator roles with JWT authentication |
| **Electron desktop app** | Kiosk mode, multi-window support, draggable camera grid |
| **Docker orchestration** | Full stack runs with a single `docker compose up` |

---

## Architecture

The system is split into two logical tiers:

### Cloud Tier
Runs on a server or VM. Handles AI processing, data persistence, and API.

| Service | Port | Technology | Role |
|---|---|---|---|
| `backend` | 8000 | FastAPI + PostgreSQL | REST API, auth, WebSocket, event storage |
| `ai_service` | 5000 | FastAPI + YOLOv8 | Object detection, tracking, zone analysis |
| `postgres` | 5432 | PostgreSQL 16 | Persistent storage for events, zones, users |
| `rabbitmq` | 5672 / 15672 | RabbitMQ 3 | Async messaging between AI → Backend and Backend → AI |

### Local Tier
Runs on-site, close to the cameras.

| Service | Port | Technology | Role |
|---|---|---|---|
| `frame_extractor` | 8100 | FastAPI + OpenCV | RTSP frame capture and forwarding to AI |
| `frontend` | 3000 / 80 | React + Electron | Desktop UI for monitoring and management |
| `mediamtx` | 8554 / 8888 / 8889 | MediaMTX | RTSP hub; serves WebRTC and HLS to the frontend |

### Data Flows

**Camera → Alert pipeline:**
```
ffmpeg (cam publisher)
  → MediaMTX :8554/cameraX   [RTSP]
  → Frame Extractor           [reads frames at DEFAULT_FPS]
  → AI Service POST /detect   [JPEG + camera_id]
  → YOLO detection + tracking
  → Zone intersection
  → Risk engine + smart analytics
  → RabbitMQ "security.events" exchange  [topic: events.{type}.{camera_id}]
  → Backend EventConsumer
  → PostgreSQL (persist)
  → WebSocket broadcast       [to all connected frontend clients]
  → Frontend alert overlay
```

**Zone update pipeline:**
```
Frontend draw/edit zone
  → Backend PUT /api/zones/{id}
  → PostgreSQL (persist)
  → RabbitMQ "security.zones" exchange   [routing: zones.updated.{camera_id}]
  → AI Service zone cache invalidation   [hot-reload, no restart needed]
```

### RabbitMQ Topology

| Exchange | Type | Published by | Consumed by |
|---|---|---|---|
| `security.events` | topic | AI Service | Backend (binding `events.#`) |
| `security.zones` | topic | Backend | AI Service (exclusive queue) |

---

## Services

### Backend Service (`cloud/backend_service/`)

FastAPI application with clean architecture layers (presentation → application → domain → infrastructure).

**Responsibilities:**
- JWT authentication (access + refresh tokens, admin/operator roles)
- Zone CRUD (create, list, update, delete)
- Event ingestion from RabbitMQ and storage in PostgreSQL
- WebSocket broadcast of real-time events to the frontend
- Zone update notifications to AI service via RabbitMQ

**Default admin credentials** (created on first start):
- Username: `admin`
- Password: `admin` *(change in production!)*

---

### AI Model Service (`cloud/ai_model_service/`)

FastAPI application with a multi-step detection pipeline.

**Detection pipeline (per frame):**
1. **YOLOv8** — object detection (person, car, knife, etc.)
2. **Tracker** — assigns persistent `track_id` per camera
3. **Zone intersection** — checks which zones each track occupies
4. **Risk engine** — applies zone rules (e.g., person in restricted → HIGH)
5. **Smart analytics** — loitering, crowding, abandoned object, direction
6. **RabbitMQ publish** — `SecurityEvent` JSON to `security.events`
7. **Evidence storage** — saves annotated JPEG for zone-triggered events

**Zone types and default rules:**

| Zone Type | Trigger Condition | Risk Level |
|---|---|---|
| `restricted` | Any object enters | HIGH |
| `pedestrian` | Vehicle enters | HIGH |
| `parking` | Person (not vehicle) enters | MEDIUM |
| `entrance` | Any motion (after hours) | MEDIUM |
| `perimeter` | Any motion | MEDIUM |
| `counting_line` | Object crosses line | LOW |
| `safe_zone` | Risk accumulation reduced | — |

---

### Frame Extractor Service (`local/frame_extractor_service/`)

FastAPI application that manages a pool of camera workers.

**Responsibilities:**
- Maintains RTSP connections to MediaMTX for each camera
- Throttles frame extraction to `DEFAULT_FPS` (default: 2.0)
- Encodes frames as JPEG and forwards to AI Service
- Persists camera configurations in SQLite
- Rewrites `localhost` RTSP URLs to `mediamtx` for Docker networking

**Camera worker lifecycle:** `STOPPED → CONNECTING → RUNNING → ERROR → CONNECTING → …`

---

### Frontend Service (`local/frontend_service/`)

Electron + React desktop application.

**Pages:**
- **Monitoring** — live RTSP stream (WebRTC), zone drawing, real-time event feed
- **Cameras Grid** — multi-camera view with per-camera alert overlays
- **Analytics** — event statistics, risk distribution charts, heatmaps
- **Settings** — camera management, connection settings, display grid configuration, access control

**Key features:**
- Draws and edits detection zones directly on the video feed
- WebSocket connection to backend for real-time event streaming
- Kiosk mode for dedicated monitoring stations
- Multi-window support with isolated localStorage state
- Automatic token refresh (JWT)

---

## Quick Start

### Prerequisites

- Docker ≥ 24 and Docker Compose ≥ 2.20
- Two camera video files placed in `./video/cam1.mp4` and `./video/cam2.mp4`  
  *(optionally `cam3.mp4` for a third camera)*

### 1. Clone and start

```bash
git clone https://github.com/T0ks1k24/secure-monitoring-system.git
cd secure-monitoring-system

# Copy the video files (not tracked in git):
# cp /your/video.mp4 ./video/cam1.mp4
# cp /your/video2.mp4 ./video/cam2.mp4

# Start all services
docker compose up -d

# Or use the Makefile:
make docker-start-d
```

### 2. Wait for services to be ready

```bash
docker compose ps          # all services should be "healthy"
docker compose logs -f     # watch startup logs
```

Typical startup order: `postgres` → `rabbitmq` → `backend` → `ai_service` → `frame_extractor`

### 3. Open the frontend

The web frontend is available at **http://localhost:3000**

For the Electron desktop app, run locally:
```bash
cd local/frontend_service/frontend
npm install
npm run electron:dev
```

### 4. Log in

- **Username:** `admin`  
- **Password:** `admin`

### 5. Add a camera

1. Go to **Settings → Camera Settings → Add Camera**
2. Enter RTSP URL: `rtsp://localhost:8554/camera1`
3. The frame extractor starts capturing; events appear within seconds

---

## Configuration

### Environment Variables

#### Backend Service (`cloud/backend_service/backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./local.db` | PostgreSQL connection string |
| `RABBITMQ_URL` | `amqp://guest:guest@rabbitmq:5672/` | RabbitMQ AMQP URL |
| `JWT_SECRET` | `SUPER_SECRET_KEY` | **Change in production!** |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token lifetime |
| `EVENTS_EXCHANGE` | `security.events` | RabbitMQ events exchange name |
| `ZONES_EXCHANGE` | `security.zones` | RabbitMQ zones exchange name |
| `EVENTS_QUEUE` | `backend.events` | Durable queue for backend consumption |

#### AI Model Service (`cloud/ai_model_service/.env`)

| Variable | Default | Description |
|---|---|---|
| `BACKEND_API_URL` | `http://backend:8000` | URL to fetch zones from backend |
| `RABBITMQ_URL` | `amqp://guest:guest@rabbitmq:5672/` | RabbitMQ connection |
| `MODEL_PATH` | `yolo26s.pt` | Path to YOLO model weights |
| `DETECTION_CONFIDENCE` | `0.4` | Detection confidence threshold (0.0–1.0) |
| `DETECTION_IOU` | `0.45` | NMS IoU threshold |
| `INFERENCE_IMG_SIZE` | `640` | YOLO input size (320 / 640 / 1280) |
| `DEVICE` | `cpu` | Inference device: `cpu`, `cuda`, `mps` |
| `SAVE_PROCESSED_FRAMES` | `False` | Save annotated frames to disk |
| `EVIDENCE_PUBLIC_BASE_URL` | `http://localhost:5000` | Public URL for evidence image links |
| `ZONE_CACHE_TTL` | `30.0` | Zone cache TTL in seconds |
| `DEBUG_VISUALIZE` | `False` | Show cv2.imshow debug windows |

#### Frame Extractor Service (`local/frame_extractor_service/.env`)

| Variable | Default | Description |
|---|---|---|
| `AI_SERVICE_URL` | `http://localhost:5000/api/v1/detect` | AI service detect endpoint |
| `AI_REQUEST_TIMEOUT` | `5` | HTTP timeout for AI requests (seconds) |
| `DEFAULT_FPS` | `2.0` | Default frame extraction rate |
| `DEFAULT_RESIZE_WIDTH` | `1280` | Frame resize width before encoding |
| `DEFAULT_JPEG_QUALITY` | `95` | JPEG compression quality (1–100) |
| `DEFAULT_RECONNECT_DELAY` | `3` | Seconds to wait before RTSP reconnect |
| `RTSP_LOCALHOST_REWRITE_HOST` | `mediamtx` | Replace `localhost` in RTSP URLs (Docker) |
| `DATABASE_URL` | `sqlite:///./cameras.db` | SQLite path for camera config storage |

#### Frontend (`local/frontend_service/frontend/.env` or Docker build args)

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |
| `VITE_FRAME_API_URL` | `http://localhost:8100` | Frame extractor API URL |
| `VITE_MEDIA_MTX_HLS_URL` | `http://localhost:8888` | MediaMTX HLS endpoint |
| `VITE_MEDIA_MTX_WEBRTC_URL` | `http://localhost:8889` | MediaMTX WebRTC endpoint |
| `VITE_WS_EVENTS_URL` | *(derived from API URL)* | WebSocket events endpoint |

---

## API Reference

See [docs/api-reference.md](docs/api-reference.md) for the full API reference.

**Interactive docs** (when running):
- Backend: http://localhost:8000/docs
- AI Service: http://localhost:5000/docs
- Frame Extractor: http://localhost:8100/docs

---

## Development

See [docs/development.md](docs/development.md) for the development guide.

### Makefile Commands

```bash
make docker-start-d      # Start all services in background
make docker-stop         # Stop all services
make docker-rebuild      # Full rebuild (no cache)
make docker-clean        # Stop + remove volumes
make docker-logs         # Stream all logs
make docker-logs-backend # Stream backend logs only
make db-reset            # Drop and recreate the database
make db-shell            # Open psql shell
make backend-shell       # Open shell in backend container
```

---

## Project Structure

```
secure_monitoring_system/
│
├── cloud/                          # Cloud-side services
│   ├── backend_service/
│   │   └── backend/                # FastAPI backend
│   │       ├── core/               # JWT, config, WebSocket manager
│   │       ├── domain/             # Entities, enums, repository interfaces
│   │       ├── application/        # Services, DTOs
│   │       ├── infrastructure/     # SQLAlchemy models, repos, RabbitMQ
│   │       └── presentation/       # FastAPI routers (controllers)
│   │
│   └── ai_model_service/           # AI detection service
│       ├── models/                 # YOLO model loader
│       ├── services/               # Pipeline, tracker, zone manager, risk engine
│       ├── schemas/                # Pydantic event/zone schemas
│       ├── config/                 # Settings
│       └── api/                    # FastAPI routes
│
├── local/                          # On-site services
│   ├── frame_extractor_service/    # RTSP frame capture
│   │   ├── core/                   # CameraManager, CameraWorker, factory, repository
│   │   ├── core/implementations/   # RTSPFrameSource, AIClientSink
│   │   ├── detection/              # Motion detector processor
│   │   ├── api/                    # FastAPI cameras and system routes
│   │   └── schemas.py              # Pydantic request/response models
│   │
│   └── frontend_service/
│       └── frontend/
│           ├── electron/           # Electron main process + preload
│           └── src/
│               ├── components/     # Reusable React components
│               ├── hooks/          # useEventStream, useKioskMode
│               ├── pages/          # Monitoring, CamerasGrid, Analytics, Settings
│               ├── services/       # RTK Query API slices (camerasApi, zonesApi, eventsApi)
│               │   └── auth/       # baseQueryWithRefresh, authSlice
│               ├── store/          # Redux store
│               └── utils/          # windowStorage
│
├── mediamtx/
│   └── mediamtx.yml                # MediaMTX configuration
│
├── video/                          # Camera test videos (not in git)
│   ├── cam1.mp4
│   ├── cam2.mp4
│   └── cam3.mp4
│
├── docker-compose.yml              # Full stack (development + production)
├── docker-compose.local.yml        # Local-only (frontend + frame_extractor)
├── docker-compose.cloud.yml        # Cloud-only (backend + AI + infra)
├── Makefile                        # Convenience commands
└── docs/
    ├── architecture.md             # Detailed architecture documentation
    ├── api-reference.md            # Complete API reference
    └── development.md              # Developer guide
```

---

## License

This project was developed as a graduation thesis at Lutsk National Technical University (LNTU), specialty 126 — Information Systems and Technologies.
