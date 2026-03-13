"""Tests for API routes — every endpoint with success and error responses."""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from schemas import (
    CameraConfig,
    CameraStatusResponse,
    MotionConfig,
)
from core.camera_manager import CameraManager
from api.deps import get_camera_manager
from service.api.routes import router


def _make_response(cam_id: str = "cam1") -> CameraStatusResponse:
    """Build a minimal CameraStatusResponse for test assertions."""
    return CameraStatusResponse(
        id=cam_id,
        name="Test",
        rtsp="rtsp://test",
        status="stopped",
        fps=2.0,
        resize_width=1280,
        jpeg_quality=95,
        frames_sent=0,
        frames_failed=0,
        frames_skipped=0,
        motion_events=0,
        motion_active=False,
        enabled=True,
        motion=MotionConfig(),
    )


def _create_test_app(mock_manager: MagicMock) -> FastAPI:
    """Create a test FastAPI app with a mocked CameraManager."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_camera_manager] = lambda: mock_manager
    return app


class TestCamerasListEndpoint(unittest.TestCase):

    def test_list_cameras_returns_200(self):
        mgr = MagicMock()
        mgr.get_all.return_value = [_make_response("c1"), _make_response("c2")]
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.get("/api/v1/cameras")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)


class TestCamerasGetOneEndpoint(unittest.TestCase):

    def test_get_camera_returns_200(self):
        mgr = MagicMock()
        mgr.get_one.return_value = _make_response("c1")
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.get("/api/v1/cameras/c1")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["id"], "c1")

    def test_get_camera_not_found_returns_404(self):
        mgr = MagicMock()
        mgr.get_one.side_effect = KeyError("Camera 'ghost' not found")
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.get("/api/v1/cameras/ghost")

        self.assertEqual(resp.status_code, 404)


class TestCamerasAddEndpoint(unittest.TestCase):

    def test_add_camera_returns_201(self):
        mgr = MagicMock()
        mgr.add_camera.return_value = _make_response("new1")
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.post("/api/v1/cameras", json={"id": "new1", "rtsp": "rtsp://new"})

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["id"], "new1")

    def test_add_camera_duplicate_returns_409(self):
        mgr = MagicMock()
        mgr.add_camera.side_effect = ValueError("Camera 'dup' already exists")
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.post("/api/v1/cameras", json={"id": "dup", "rtsp": "rtsp://dup"})

        self.assertEqual(resp.status_code, 409)

    def test_add_camera_missing_required_field_returns_422(self):
        mgr = MagicMock()
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.post("/api/v1/cameras", json={"id": "x"})  # missing rtsp

        self.assertEqual(resp.status_code, 422)


class TestCamerasUpdateEndpoint(unittest.TestCase):

    def test_update_camera_returns_200(self):
        mgr = MagicMock()
        mgr.update_camera.return_value = _make_response("c1")
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.patch("/api/v1/cameras/c1", json={"fps": 5.0})

        self.assertEqual(resp.status_code, 200)

    def test_update_camera_not_found_returns_404(self):
        mgr = MagicMock()
        mgr.update_camera.side_effect = KeyError("not found")
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.patch("/api/v1/cameras/ghost", json={"fps": 5.0})

        self.assertEqual(resp.status_code, 404)


class TestCamerasDeleteEndpoint(unittest.TestCase):

    def test_remove_camera_returns_204(self):
        mgr = MagicMock()
        mgr.remove_camera = AsyncMock()
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.delete("/api/v1/cameras/c1")

        self.assertEqual(resp.status_code, 204)

    def test_remove_camera_not_found_returns_404(self):
        mgr = MagicMock()
        mgr.remove_camera = AsyncMock(side_effect=KeyError("not found"))
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.delete("/api/v1/cameras/ghost")

        self.assertEqual(resp.status_code, 404)


class TestCamerasStartEndpoint(unittest.TestCase):

    def test_start_camera_returns_200(self):
        mgr = MagicMock()
        mgr.start_camera.return_value = _make_response("c1")
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.post("/api/v1/cameras/c1/start")

        self.assertEqual(resp.status_code, 200)

    def test_start_camera_not_found_returns_404(self):
        mgr = MagicMock()
        mgr.start_camera.side_effect = KeyError("not found")
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.post("/api/v1/cameras/ghost/start")

        self.assertEqual(resp.status_code, 404)


class TestCamerasStopEndpoint(unittest.TestCase):

    def test_stop_camera_returns_200(self):
        mgr = MagicMock()
        mgr.stop_camera = AsyncMock(return_value=_make_response("c1"))
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.post("/api/v1/cameras/c1/stop")

        self.assertEqual(resp.status_code, 200)

    def test_stop_camera_not_found_returns_404(self):
        mgr = MagicMock()
        mgr.stop_camera = AsyncMock(side_effect=KeyError("not found"))
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.post("/api/v1/cameras/ghost/stop")

        self.assertEqual(resp.status_code, 404)


class TestHealthEndpoint(unittest.TestCase):

    def test_health_returns_200(self):
        mgr = MagicMock()
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.get("/api/v1/health")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")


class TestStatusEndpoint(unittest.TestCase):

    @patch("api.system.settings")
    def test_status_returns_200_with_counts(self, mock_settings):
        mock_settings.AI_SERVICE_URL = "http://test"
        mock_settings.DEFAULT_FPS = 2.0
        mock_settings.DEFAULT_RESIZE_WIDTH = 1280
        mock_settings.DEFAULT_JPEG_QUALITY = 95

        mgr = MagicMock()
        running = _make_response("c1")
        running.status = "running"
        mgr.get_all.return_value = [running, _make_response("c2")]
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.get("/api/v1/status")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["active_cameras"], 1)
        self.assertEqual(data["total_cameras"], 2)


class TestConfigEndpoint(unittest.TestCase):

    def test_update_config_returns_200(self):
        mgr = MagicMock()
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.patch(
                "/api/v1/config",
                json={"ai_service_url": "http://new-ai:5000"},
            )

        self.assertEqual(resp.status_code, 200)
        mgr.update_global_config.assert_called_once()


class TestScannerSearchGetEndpoint(unittest.TestCase):

    @patch("api.scanner.scan_network")
    def test_search_get_returns_200(self, mock_scan):
        from schemas import ScanResult
        mock_scan.return_value = ScanResult(
            subnet="192.168.1.0/24",
            ports_scanned=[554],
            hosts_scanned=254,
            found=[],
            scan_duration_sec=1.0,
        )
        mgr = MagicMock()
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.get("/api/v1/scanner/search?subnet=192.168.1.0/24&ports=554")

        self.assertEqual(resp.status_code, 200)

    def test_search_get_invalid_ports_returns_400(self):
        mgr = MagicMock()
        app = _create_test_app(mgr)

        with TestClient(app) as client:
            resp = client.get("/api/v1/scanner/search?ports=abc")

        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
