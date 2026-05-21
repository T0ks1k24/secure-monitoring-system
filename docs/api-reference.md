# API Reference

This document covers all HTTP endpoints exposed by the three backend services.  
Interactive Swagger UI is available at `/docs` on each running service.

---

## Table of Contents

- [Backend Service — :8000](#backend-service--8000)
  - [Health & Readiness](#health--readiness)
  - [Authentication](#authentication)
  - [Events](#events)
  - [Zones](#zones)
  - [Server Info](#server-info)
  - [WebSocket](#websocket)
- [AI Model Service — :5000](#ai-model-service--5000)
  - [Detection](#detection)
  - [Health & Status](#health--status)
  - [Settings](#settings)
- [Frame Extractor Service — :8100](#frame-extractor-service--8100)
  - [Cameras](#cameras)
  - [System / Config](#system--config)

---

## Backend Service — :8000

Base URL: `http://localhost:8000`

### Health & Readiness

#### `GET /health`
Returns `200 OK` as soon as the process is running (liveness probe).

```json
{ "status": "ok" }
```

#### `GET /ready`
Returns `200` only after all startup tasks complete (RabbitMQ, DB migrations, admin seed).  
Returns `503` while still initialising.

```json
{ "status": "ready" }
```

---

### Authentication

All protected endpoints require the header:
```
Authorization: Bearer <access_token>
```

#### `POST /auth/login`

Authenticate with username and password.

**Request body:**
```json
{
  "username": "admin",
  "password": "admin"
}
```

**Response `200`:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ..."
}
```

**Response `401`:** Invalid credentials.

---

#### `POST /auth/refresh`

Obtain a new access token using a valid refresh token.

**Request body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response `200`:**
```json
{
  "access_token": "eyJ..."
}
```

**Response `401`:** Token expired, invalid, wrong type, or user deleted.

---

#### `GET /auth/users` *(admin only)*

List all users.

**Response `200`:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "admin",
    "role": "admin",
    "created_at": "2026-01-01T00:00:00"
  }
]
```

---

#### `GET /auth/users/{user_id}` *(admin only)*

Get a single user by UUID.

**Response `200`:** `UserResponse` object.  
**Response `404`:** User not found.

---

#### `POST /auth/users` *(admin only)*

Create a new user.

**Request body:**
```json
{
  "username": "operator1",
  "password": "SecurePass123",
  "role": "operator"
}
```

**Roles:** `admin` | `operator`

**Response `200`:**
```json
{
  "id": "uuid",
  "username": "operator1",
  "role": "operator"
}
```

---

#### `POST /auth/reset-password` *(admin only)*

Reset a user's password.

**Request body:**
```json
{
  "user_id": "uuid",
  "new_password": "NewSecurePass123"
}
```

**Response `200`:** `{ "status": "password_updated" }`

---

### Events

#### `GET /events/` *(requires auth)*

Retrieve all stored security events, sorted by insertion order.

**Response `200`:**
```json
[
  {
    "id": "event-uuid",
    "camera_id": "1",
    "event_type": "zone_intrusion",
    "object_class": "person",
    "track_id": 42,
    "confidence": 0.91,
    "zone_id": "15",
    "zone_name": "Restricted Area A",
    "bbox": { "x1": 0.21, "y1": 0.34, "x2": 0.42, "y2": 0.88 },
    "metadata": {
      "evidence_url": "http://localhost:5000/evidence/cam1/frame_1234.jpg",
      "mode": "STRICT"
    },
    "timestamp": "2026-05-01T14:30:00.000000",
    "risk": "HIGH"
  }
]
```

**Risk levels:** `LOW` | `MEDIUM` | `HIGH` | `CRITICAL`

**Event types:**

| Type | Description |
|---|---|
| `person_detected` | A person was detected |
| `vehicle_detected` | A vehicle was detected |
| `weapon_detected` | A weapon was detected (always CRITICAL) |
| `zone_intrusion` | Object entered a restricted zone |
| `zone_loitering` | Object remained in zone beyond threshold |
| `zone_crowding` | Too many people in zone |
| `zone_smart_activity` | Smart presence analytics triggered |
| `running_detected` | Fast movement detected |
| `direction_violation` | Movement against allowed direction |
| `abandoned_object` | Object left stationary |
| `camera_offline` | Camera stream lost |

---

### Zones

#### `POST /api/zones/`

Create a detection zone for a camera.

**Request body:**
```json
{
  "name": "Restricted Area A",
  "camera_id": "camera1",
  "polygon": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]],
  "zone_type": "restricted",
  "risk_weight": 30.0,
  "is_active": true,
  "max_people_allowed": 0,
  "cooldown_seconds": 5.0,
  "base_mode": "STRICT",
  "time_windows": [
    { "start": "09:00", "end": "17:00" }
  ],
  "risk_multipliers": { "relaxed": 0.3, "strict": 1.5 },
  "people_thresholds": { "medium": 2, "high": 5 },
  "accumulation": { "decay_per_second": 1.0 }
}
```

**Zone types:** `restricted` | `perimeter` | `parking` | `entrance` | `pedestrian` | `counting_line` | `safe_zone`

> **Polygon format:** List of `[x, y]` pairs in normalised coordinates (0.0–1.0 relative to frame size). Minimum 3 points.

**Time windows** define RELAXED mode periods. Outside these windows, the zone operates in STRICT mode (multiplied risk).

**Response `200`:** Full `ZoneResponseDTO` with assigned `id`.

---

#### `GET /api/zones/{camera_id}`

List all active zones for a camera.

**Path parameter:** `camera_id` — the camera identifier (e.g. `camera1`, `1`)

**Response `200`:** Array of `ZoneResponseDTO`.

---

#### `PUT /api/zones/{zone_id}`

Update an existing zone. All fields are optional (partial update).

**Path parameter:** `zone_id` — integer zone ID

**Request body:** Any subset of zone fields (same schema as create, all nullable).

**Response `200`:** Updated `ZoneResponseDTO`.  
**Response `404`:** Zone not found.

> Zone updates are automatically published to RabbitMQ, invalidating the AI service cache within milliseconds.

---

#### `DELETE /api/zones/{zone_id}`

Delete a zone by ID.

**Response `200`:** `{ "deleted": true }`  
**Response `404`:** Zone not found.

---

### Server Info

#### `GET /server/info`

Returns the server's local and public IP addresses. Used by the frontend to discover the backend URL.

**Response `200`:**
```json
{
  "local_ip": "192.168.1.100",
  "public_ip": "203.0.113.42"
}
```

---

### WebSocket

#### `WS /ws/events`

Real-time event stream. Connect once; every new security event is pushed immediately.

**Connection:** `ws://localhost:8000/ws/events`

> No authentication is required for WebSocket — rely on network-level access control in production.

**Message format** (same as `GET /events/` item):
```json
{
  "id": "event-uuid",
  "camera_id": "1",
  "event_type": "zone_intrusion",
  "object_class": "person",
  "track_id": 42,
  "confidence": 0.91,
  "timestamp": "2026-05-01T14:30:00.000000",
  "zone_id": "15",
  "zone_name": "Restricted Area A",
  "risk": "HIGH",
  "bbox": { "x1": 0.21, "y1": 0.34, "x2": 0.42, "y2": 0.88 },
  "metadata": {}
}
```

The client can send any text message to keep the connection alive (ping). Stale connections are automatically cleaned up on the next broadcast.

---

## AI Model Service — :5000

Base URL: `http://localhost:5000`

### Detection

#### `POST /api/v1/detect`

Submit a camera frame for AI analysis. Returns tracked objects and the number of events published.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `image` | file (JPEG) | ✅ | Camera frame as JPEG bytes |
| `camera_id` | string | ✅ | Camera identifier (e.g. `"1"`, `"camera1"`) |
| `stream_fps` | float | ❌ | Actual stream FPS for tracker tuning (default: `10.0`) |
| `frame_timestamp` | float | ❌ | Unix timestamp of the frame (default: `time.time()`) |

**Response `200`:**
```json
{
  "camera_id": "1",
  "frame_timestamp": 1746100000.0,
  "tracked_objects": [
    {
      "track_id": 42,
      "obj_class": "person",
      "confidence": 0.91,
      "bbox": {
        "x1": 0.21, "y1": 0.34,
        "x2": 0.42, "y2": 0.88,
        "cx": 0.315, "cy": 0.61,
        "w": 0.21, "h": 0.54
      },
      "zone_ids": ["15", "16"]
    }
  ],
  "events_published": 1,
  "processing_time_ms": 48.3
}
```

---

### Health & Status

#### `GET /api/v1/health`

Liveness probe.

```json
{ "status": "ok" }
```

#### `GET /api/v1/status`

Detailed service status: model info, zone cache stats, RabbitMQ connection state.

```json
{
  "status": "running",
  "model": "yolo26s.pt",
  "device": "cpu",
  "rabbitmq_connected": true,
  "total_cached_zones": 4,
  "active_trackers": 2
}
```

---

### Settings

#### `PATCH /api/v1/settings`

Hot-reload AI service configuration at runtime (no restart required).

**Request body** (all fields optional):
```json
{
  "detection_confidence": 0.5,
  "detection_iou": 0.4,
  "save_processed_frames": true,
  "debug_visualize": false
}
```

**Response `200`:** `{ "status": "updated" }`

---

### Evidence Files

Annotated evidence frames are served as static files:

```
GET http://localhost:5000/evidence/{camera_id}/{filename}.jpg
```

The URL is included in the event `metadata.evidence_url` field.

---

## Frame Extractor Service — :8100

Base URL: `http://localhost:8100`

### Cameras

#### `GET /api/v1/cameras`

List all configured cameras with live status.

**Response `200`:**
```json
[
  {
    "id": 1,
    "name": "Entrance Camera",
    "rtsp": "rtsp://mediamtx:8554/camera1",
    "status": "running",
    "fps": 2.0,
    "resize_width": 1280,
    "jpeg_quality": 95,
    "frames_sent": 1042,
    "frames_failed": 3,
    "frames_skipped": 0,
    "motion_events": 18,
    "motion_active": false,
    "enabled": true,
    "motion": {
      "enabled": false,
      "threshold": 25,
      "min_contour_area": 500,
      "min_duration": 0.5
    }
  }
]
```

**Camera statuses:** `stopped` | `connecting` | `running` | `error`

---

#### `GET /api/v1/cameras/{camera_id}`

Get a single camera by integer ID.

**Response `404`:** Camera not found.

---

#### `POST /api/v1/cameras`

Add a new camera and start capturing frames.

**Request body:**
```json
{
  "name": "Entrance Camera",
  "rtsp": "rtsp://192.168.1.10:554/stream",
  "enabled": true,
  "fps": 2.0,
  "resize_width": 1280,
  "jpeg_quality": 95,
  "motion": {
    "enabled": false,
    "threshold": 25,
    "min_contour_area": 500,
    "min_duration": 0.5,
    "blur_size": 21,
    "frames_to_average": 5
  }
}
```

> `localhost` and `127.0.0.1` in RTSP URLs are automatically rewritten to `mediamtx` for Docker networking.

**Response `201`:** Created camera `CameraStatusResponse`.  
**Response `400`:** Validation error (e.g. duplicate name).

---

#### `PATCH /api/v1/cameras/{camera_id}`

Update camera configuration. Only provided fields are changed.

**Request body:** Any subset of camera fields (all nullable).

**Response `200`:** Updated `CameraStatusResponse`.  
**Response `404`:** Camera not found.

---

#### `DELETE /api/v1/cameras/{camera_id}`

Stop and remove a camera.

**Response `204`:** No content.  
**Response `404`:** Camera not found.

---

#### `POST /api/v1/cameras/{camera_id}/start`

Start frame extraction for a stopped camera.

**Response `200`:** Updated `CameraStatusResponse`.

---

#### `POST /api/v1/cameras/{camera_id}/stop`

Stop frame extraction for a running camera.

**Response `200`:** Updated `CameraStatusResponse`.

---

### System / Config

#### `GET /api/v1/health`

```json
{ "status": "ok" }
```

#### `GET /api/v1/status`

```json
{
  "active_workers": 2,
  "total_cameras": 3,
  "ai_service_url": "http://ai_service:5000/api/v1/detect"
}
```

#### `GET /api/v1/config`

Get current global defaults.

```json
{
  "default_fps": 2.0,
  "default_resize_width": 1280,
  "default_jpeg_quality": 95,
  "default_reconnect_delay": 3,
  "ai_service_url": "http://ai_service:5000/api/v1/detect"
}
```

#### `PATCH /api/v1/config`

Update global defaults (affects new cameras and workers at restart).

**Request body** (all optional):
```json
{
  "ai_service_url": "http://new-ai-host:5000/api/v1/detect",
  "default_fps": 5.0,
  "default_resize_width": 640,
  "default_jpeg_quality": 80,
  "default_reconnect_delay": 5
}
```

---

## Error Responses

All services use standard HTTP status codes:

| Code | Meaning |
|---|---|
| `200` | Success |
| `201` | Created |
| `204` | No content (DELETE) |
| `400` | Bad request / validation error |
| `401` | Unauthenticated or invalid token |
| `403` | Forbidden (insufficient role) |
| `404` | Resource not found |
| `422` | Unprocessable entity (Pydantic validation) |
| `503` | Service not ready yet |

Error body format:
```json
{
  "detail": "Human-readable error message"
}
```
