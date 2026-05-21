# Architecture

This document describes the system design, component responsibilities, communication patterns, and key design decisions.

---

## Table of Contents

- [System Overview](#system-overview)
- [Component Map](#component-map)
- [Data Flows](#data-flows)
- [Service Internals](#service-internals)
- [Messaging Topology](#messaging-topology)
- [Database Schema](#database-schema)
- [Security Model](#security-model)
- [Design Decisions](#design-decisions)

---

## System Overview

The Secure Monitoring System follows a **distributed microservices architecture** split into two deployment tiers:

| Tier | Services | Location |
|---|---|---|
| **Cloud** | Backend, AI Service, PostgreSQL, RabbitMQ | Remote server / VM |
| **Local** | Frame Extractor, Frontend (Electron), MediaMTX | On-site, near cameras |

This split allows the compute-heavy AI workload to run on a server with a GPU, while the low-latency RTSP frame capture runs close to the cameras to minimise network overhead.

---

## Component Map

```
┌──────────────────────────────────────────────────────────────────┐
│ LOCAL TIER                                                       │
│                                                                  │
│  ┌─────────┐  RTSP   ┌────────────┐  JPEG   ┌────────────────┐  │
│  │ Cameras │────────►│  MediaMTX  │◄────────│Frame Extractor │  │
│  └─────────┘         └──────┬─────┘         └───────┬────────┘  │
│                 WebRTC/HLS  │                        │ HTTP POST  │
│                             ▼                        │ /detect    │
│                    ┌────────────────┐                │            │
│                    │ Electron App   │                │            │
│                    │ React+Redux    │                │            │
│                    └───────┬────────┘                │            │
│                            │ REST + WebSocket         │            │
└────────────────────────────┼─────────────────────────┼────────────┘
                             │                         │
                             ▼                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ CLOUD TIER                                                       │
│                                                                  │
│  ┌─────────────────┐  RabbitMQ  ┌─────────────────────────────┐  │
│  │  Backend (8000) │◄──────────►│    AI Service (5000)        │  │
│  │  FastAPI + PG   │            │  YOLOv8 + Tracker + Zones   │  │
│  └────────┬────────┘            └─────────────────────────────┘  │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────┐   ┌──────────────┐                              │
│  │ PostgreSQL  │   │  RabbitMQ    │                              │
│  └─────────────┘   └──────────────┘                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## Data Flows

### 1. Camera Frame → Security Event

```
[Camera RTSP stream]
        │
        │  RTSP/TCP
        ▼
[MediaMTX :8554/cameraX]
        │
        │  RTSP (pull)
        ▼
[Frame Extractor]
  - Throttle to DEFAULT_FPS (e.g. 2 fps)
  - Resize frame to DEFAULT_RESIZE_WIDTH
  - Encode as JPEG (DEFAULT_JPEG_QUALITY)
        │
        │  HTTP multipart/form-data
        │  POST /api/v1/detect
        │  fields: image, camera_id, stream_fps
        ▼
[AI Service — AnalyzePipeline.process()]
  Step 1: YOLOv8 detect(frame)
          → List[(BBox, class, confidence)]
  Step 2: Tracker.update(detections, zone_ids)
          → List[Track] with persistent track_id
  Step 3: ZoneManager.find_zones_for_object()
          → Dict[track_id → List[Zone]]  (feet-point intersection)
  Step 4: RiskEngine.analyze()
          → List[SecurityEvent]  (zone rules)
  Step 5: SmartZoneAnalytics.analyze()
          → Additional events (loitering, crowding, direction)
  Step 6: FrameStorage.save_frame()  (if zone events)
          → evidence JPEG saved to disk
  Step 7: RabbitMQ.publish_events()
          → exchange: security.events
          → routing_key: events.{event_type}.{camera_id}
        │
        │  AMQP message (JSON)
        ▼
[Backend EventConsumer]
  - Deserialise AIEventDTO
  - EventService.ingest_ai_event()
      → Deduplicate by event_id
      → Persist to PostgreSQL
  - WebSocket.broadcast(payload)
        │
        │  WebSocket JSON message
        ▼
[Frontend useEventStream hook]
  - Prepend to events state (max 200)
  - Monitoring page: filter by camera
  - CamerasGrid: show alert overlay
```

### 2. Zone Update → AI Cache Invalidation

```
[Frontend — zone draw/edit]
        │
        │  PUT /api/zones/{id}
        ▼
[Backend ZoneService.update()]
  - zone_repo.update()      → PostgreSQL
  - rabbitmq_client.publish_zone_update(camera_id)
        │
        │  AMQP message
        │  exchange: security.zones
        │  routing_key: zones.updated.{camera_id}
        ▼
[AI Service — RabbitMQService._on_zone_message()]
  - ZoneManager.invalidate(camera_id)
        │
        ▼
[Next frame for that camera]
  - ZoneManager.get_zones(camera_id)  → HTTP GET /api/zones/{camera_id}
  - Cache refreshed with new zones
```

### 3. Frontend Authentication

```
[Login page]
        │  POST /auth/login
        ▼
[Backend] → JWT access token (15 min) + refresh token (30 days)
        │
        ▼
[Frontend authSlice] → stores in Redux state + localStorage
        │
[Every API request]  → Authorization: Bearer {access_token}
        │
[baseQueryWithRefresh]
  - if 401 → POST /auth/refresh with refresh_token
  - if refresh OK → update access_token, retry original request
  - if refresh fails → dispatch logOut()
```

---

## Service Internals

### AI Model Service — Pipeline Detail

```
AnalyzePipeline.process(frame, request)
│
├── detector.detect(frame)
│   └── YOLOv8(frame, conf=0.4, iou=0.45, max_det=50)
│       returns: [(BoundingBox, class_name, confidence), ...]
│
├── tracker_registry.get(camera_id, fps)
│   └── CameraTracker.update(detections, zone_ids)
│       ├── IoU matching against existing tracks
│       ├── Assign new track_id for unmatched detections
│       ├── Age out stale tracks (TRACKER_MAX_AGE_SECONDS)
│       └── Return only confirmed tracks (≥ TRACKER_MIN_HITS)
│
├── zone_manager.get_zones(camera_id)          ← cached, TTL=30s
│   └── HTTP GET /api/zones/{camera_id}
│
├── for each track: zone_manager.find_zones_for_object()
│   └── bbox_intersects_polygon(cx, cy, x1,y1,x2,y2, polygon, mode="feet")
│       ← checks the foot-point (cx, y2) for person objects
│
├── risk_engine.analyze(camera_id, tracks, zone_memberships)
│   └── For each (zone, track) pair:
│       ├── Look up ZoneRule for zone_type + object_class
│       ├── Check trigger_after_seconds (dwell time)
│       ├── EventDeduplicator.should_fire() — cooldown guard
│       └── Emit SecurityEvent if all conditions met
│
├── smart_zone_analytics.analyze(...)
│   └── Per (camera_id, zone_id) state:
│       ├── Crowding: count people > zone.people_thresholds
│       ├── Loitering: dwell_time > threshold
│       ├── Direction violation: trajectory angle check
│       └── Abandoned object: stationary non-person detection
│
├── frame_storage.save_frame()   ← if zone events present
│   └── Saves annotated JPEG with overlays as evidence
│
└── rabbitmq_service.publish_events(events)
    └── SecurityEvent → JSON → AMQP message
```

### Frame Extractor — Camera Worker

Each camera has a dedicated `CameraWorker` async task:

```
CameraWorker._run() loop:
  while not stop_event:
    1. Connect RTSP (RTSPFrameSource → cv2.VideoCapture via executor)
    2. Read frame (run_in_executor to avoid blocking event loop)
    3. Throttle: skip if (now - last_process_time) < 1/fps
    4. Process pipeline:
       - MotionDetectorProcessor (optional, skips static frames)
    5. Send to sinks:
       - AIClientSink → AIClient.send_frame() → HTTP POST /detect
    6. Update stats (frames_sent / frames_failed / frames_skipped)
```

### Backend — Clean Architecture Layers

```
presentation/    ← FastAPI routers, request/response DTOs
application/     ← Use cases, business logic, DTOs
domain/          ← Entities, repository interfaces, enums (no framework deps)
infrastructure/  ← SQLAlchemy models, repo implementations, RabbitMQ clients
core/            ← JWT auth, config, WebSocket manager, startup helpers
```

---

## Messaging Topology

### Exchanges

| Exchange | Type | Durable | Description |
|---|---|---|---|
| `security.events` | topic | ✅ | AI → Backend: security events |
| `security.zones` | topic | ✅ | Backend → AI: zone config updates |

### Queues

| Queue | Exchange | Binding | Durable | Description |
|---|---|---|---|---|
| `backend.events` | `security.events` | `events.#` | ✅ | Backend receives all events |
| *(exclusive, auto-delete)* | `security.zones` | `zones.updated.#` | ❌ | Per-AI-instance zone updates |

### Routing Keys

**AI Service publishes:**
```
events.{event_type}.{camera_id}
events.zone_intrusion.camera1
events.weapon_detected.1
```

**Backend publishes:**
```
zones.updated.{camera_id}
zones.updated.camera1
```

### Message Persistence

- Events: `delivery_mode=PERSISTENT` (survive broker restart)
- Zone updates: `delivery_mode=PERSISTENT` (avoid missed updates)

---

## Database Schema

### PostgreSQL (Backend)

```sql
-- Users
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username    VARCHAR UNIQUE NOT NULL,
    password    VARCHAR NOT NULL,        -- bcrypt hash
    role        VARCHAR NOT NULL,        -- 'admin' | 'operator'
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Detection Zones
CREATE TABLE zones (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR NOT NULL,
    camera_id           VARCHAR NOT NULL,
    polygon             JSONB NOT NULL,   -- [[x,y], ...]  normalised 0..1
    zone_type           VARCHAR NOT NULL,
    risk_weight         FLOAT NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    max_people_allowed  INT NOT NULL DEFAULT 0,
    time_windows        JSONB NOT NULL DEFAULT '[]',
    base_mode           VARCHAR NOT NULL DEFAULT 'STRICT',
    risk_multipliers    JSONB NOT NULL,
    people_thresholds   JSONB NOT NULL,
    accumulation        JSONB NOT NULL,
    cooldown_seconds    FLOAT NOT NULL DEFAULT 5.0
);

-- Security Events
CREATE TABLE events (
    id              VARCHAR PRIMARY KEY,   -- UUID from AI service
    camera_id       VARCHAR NOT NULL,
    event_type      VARCHAR NOT NULL,
    object_class    VARCHAR,
    track_id        INT,
    confidence      FLOAT,
    timestamp       TIMESTAMP NOT NULL,
    zone_id         VARCHAR,
    zone_name       VARCHAR,
    risk            VARCHAR NOT NULL,      -- LOW|MEDIUM|HIGH|CRITICAL
    bbox            JSONB,
    event_metadata  JSONB NOT NULL DEFAULT '{}'
);
```

### SQLite (Frame Extractor)

```sql
CREATE TABLE cameras (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    rtsp          TEXT NOT NULL,
    enabled       BOOLEAN NOT NULL DEFAULT 1,
    fps           REAL,
    resize_width  INTEGER,
    jpeg_quality  INTEGER,
    motion_json   TEXT NOT NULL DEFAULT '{}'   -- MotionConfig as JSON
);
```

---

## Security Model

### Authentication

- **JWT RS256** tokens signed with `JWT_SECRET`
- **Access token** lifetime: 15 minutes (configurable)
- **Refresh token** lifetime: 30 days (configurable)
- Refresh tokens are stored client-side (localStorage); invalidated if user is deleted
- Password hashing: **bcrypt**

### Authorisation

| Resource | Public | Authenticated | Admin only |
|---|---|---|---|
| `GET /health` | ✅ | — | — |
| `GET /ready` | ✅ | — | — |
| `POST /auth/login` | ✅ | — | — |
| `POST /auth/refresh` | ✅ | — | — |
| `GET /events/` | — | ✅ | — |
| `GET /api/zones/{id}` | ✅ | — | — |
| `POST /api/zones/` | ✅ | — | — |
| `PUT /api/zones/{id}` | ✅ | — | — |
| `DELETE /api/zones/{id}` | ✅ | — | — |
| `GET /auth/users` | — | — | ✅ |
| `POST /auth/users` | — | — | ✅ |
| `POST /auth/reset-password` | — | — | ✅ |
| `WS /ws/events` | ✅ | — | — |

> Zone management endpoints are intentionally public to allow the AI service to fetch zones without a service account.

### CORS

All services allow all origins (`*`) for development. Restrict in production:
```python
allow_origins=["https://your-frontend-domain.com"]
```

---

## Design Decisions

### Why RabbitMQ instead of direct HTTP calls?

RabbitMQ decouples AI from Backend: if the backend restarts or is slow, events are queued and processed when it recovers. This prevents event loss under load and enables independent scaling.

### Why separate Frame Extractor from AI?

Frame extraction is I/O-bound (RTSP network), while AI is CPU/GPU-bound. Separating them lets both scale independently and keeps the AI service stateless (no RTSP connection management).

### Why SQLite in Frame Extractor?

Camera configuration is small, local, and does not need distribution. SQLite avoids an external dependency for the local tier and simplifies deployment on edge hardware.

### Why zone coordinates are normalised (0.0–1.0)?

Zones are drawn relative to frame dimensions. If the resolution changes (e.g. different camera), the zones remain valid without recalculation.

### Why topic exchange instead of direct?

Topic routing (`events.{type}.{camera_id}`) allows future consumers to subscribe to a subset of events (e.g. `events.weapon_detected.*`) without the AI service needing to know about them.

### Why Electron instead of web-only?

Electron enables:
- Local RTSP stream access without CORS or certificate issues
- Kiosk mode for dedicated monitoring stations
- Multi-window isolation (each operator window has its own state)
- `ffmpeg-static` for in-process camera publishing in development
