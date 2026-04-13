"""Tests for API routes — every endpoint with success and error responses."""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from schemas import CameraStatusResponse, MotionConfig
from core.camera_manager import CameraManager
from api.deps import get_camera_manager
from service.api.routes import router


def _make_response(cam_id: int = 1) -> CameraStatusResponse:
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


def _get_app(mgr):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_camera_manager] = lambda: mgr
    return app


class TestCamerasListEndpoint(unittest.TestCase):
    """Test suite for the cameras list endpoint."""

    def test_list_cameras_returns_200(self):
        mgr = MagicMock()
        mgr.get_all.return_value = [_make_response(1), _make_response(2)]
        client = TestClient(_get_app(mgr))

        resp = client.get("/cameras")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)


class TestCamerasGetOneEndpoint(unittest.TestCase):
    """Test suite for the single camera retrieval endpoint."""

    def test_get_camera_returns_200(self):
        mgr = MagicMock()
        mgr.get_one.return_value = _make_response(10)
        client = TestClient(_get_app(mgr))

        resp = client.get("/cameras/10")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["id"], 10)

    def test_get_camera_not_found_returns_404(self):
        mgr = MagicMock()
        mgr.get_one.side_effect = KeyError("Not found")
        client = TestClient(_get_app(mgr))

        resp = client.get("/cameras/999")
        self.assertEqual(resp.status_code, 404)


class TestCamerasAddEndpoint(unittest.TestCase):
    """Test suite for the camera addition endpoint."""

    def test_add_camera_returns_201(self):
        mgr = MagicMock()
        mgr.add_camera.return_value = _make_response(5)
        client = TestClient(_get_app(mgr))

        payload = {"name": "New", "rtsp": "rtsp://new"}
        resp = client.post("/cameras", json=payload)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["id"], 5)

    def test_add_camera_validation_error_returns_400(self):
        mgr = MagicMock()
        mgr.add_camera.side_effect = ValueError("Invalid RTSP")
        client = TestClient(_get_app(mgr))

        payload = {"name": "Bad", "rtsp": "rtsp://bad"}
        resp = client.post("/cameras", json=payload)
        self.assertEqual(resp.status_code, 400)


class TestCamerasUpdateEndpoint(unittest.TestCase):
    """Test suite for the camera update endpoint."""

    def test_update_camera_returns_200(self):
        mgr = MagicMock()
        mgr.update_camera.return_value = _make_response(1)
        client = TestClient(_get_app(mgr))

        payload = {"name": "Updated"}
        resp = client.patch("/cameras/1", json=payload)
        self.assertEqual(resp.status_code, 200)
        mgr.update_camera.assert_called_once()

    def test_update_camera_not_found_returns_404(self):
        mgr = MagicMock()
        mgr.update_camera.side_effect = KeyError("No such camera")
        client = TestClient(_get_app(mgr))

        resp = client.patch("/cameras/1", json={"name": "X"})
        self.assertEqual(resp.status_code, 404)


class TestCamerasDeleteEndpoint(unittest.TestCase):
    """Test suite for the camera deletion endpoint."""

    def test_remove_camera_returns_204(self):
        mgr = MagicMock()
        mgr.remove_camera = AsyncMock()
        client = TestClient(_get_app(mgr))

        resp = client.delete("/cameras/1")
        self.assertEqual(resp.status_code, 204)
        mgr.remove_camera.assert_called_once_with(1)

    def test_remove_camera_not_found_returns_404(self):
        mgr = MagicMock()
        mgr.remove_camera.side_effect = KeyError("Not found")
        client = TestClient(_get_app(mgr))

        resp = client.delete("/cameras/1")
        self.assertEqual(resp.status_code, 404)


class TestCamerasStartEndpoint(unittest.TestCase):
    """Test suite for the camera start endpoint."""

    def test_start_camera_returns_200(self):
        mgr = MagicMock()
        mgr.start_camera.return_value = _make_response(1)
        client = TestClient(_get_app(mgr))

        resp = client.post("/cameras/1/start")
        self.assertEqual(resp.status_code, 200)
        mgr.start_camera.assert_called_once_with(1)

    def test_start_camera_not_found_returns_404(self):
        mgr = MagicMock()
        mgr.start_camera.side_effect = KeyError("Not found")
        client = TestClient(_get_app(mgr))

        resp = client.post("/cameras/1/start")
        self.assertEqual(resp.status_code, 404)


class TestCamerasStopEndpoint(unittest.TestCase):
    """Test suite for the camera stop endpoint."""

    def test_stop_camera_returns_200(self):
        mgr = MagicMock()
        mgr.stop_camera = AsyncMock(return_value=_make_response(1))
        client = TestClient(_get_app(mgr))

        resp = client.post("/cameras/1/stop")
        self.assertEqual(resp.status_code, 200)
        mgr.stop_camera.assert_called_once_with(1)

    def test_stop_camera_not_found_returns_404(self):
        mgr = MagicMock()
        mgr.stop_camera.side_effect = KeyError("Not found")
        client = TestClient(_get_app(mgr))

        resp = client.post("/cameras/1/stop")
        self.assertEqual(resp.status_code, 404)


class TestHealthEndpoint(unittest.TestCase):
    """Test suite for the health check endpoint."""

    def test_health_returns_200(self):
        mgr = MagicMock()
        client = TestClient(_get_app(mgr))

        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})


class TestStatusEndpoint(unittest.TestCase):
    """Test suite for the system status endpoint."""

    @patch("api.system.settings")
    def test_status_returns_200_with_counts(self, mock_settings):
        mock_settings.AI_SERVICE_URL = "http://test"
        mgr = MagicMock()
        # 1 active, 2 total
        r1 = _make_response(1)
        r1.status = "running"
        r2 = _make_response(2)
        mgr.get_all.return_value = [r1, r2]

        client = TestClient(_get_app(mgr))
        resp = client.get("/status")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["active_workers"], 1)
        self.assertEqual(data["total_cameras"], 2)


class TestConfigEndpoint(unittest.TestCase):
    """Test suite for the global configuration endpoint."""

    def test_get_config_returns_200(self):
        mgr = MagicMock()
        mgr._settings.DEFAULT_FPS = 5.0
        mgr._settings.AI_SERVICE_URL = "http://test"
        client = TestClient(_get_app(mgr))

        resp = client.get("/config")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["default_fps"], 5.0)

    def test_update_config_returns_200(self):
        mgr = MagicMock()
        client = TestClient(_get_app(mgr))

        payload = {"ai_service_url": "http://new-ai"}
        resp = client.patch("/config", json=payload)

        self.assertEqual(resp.status_code, 200)
        mgr.update_global_config.assert_called_once_with(ai_service_url="http://new-ai")

    def test_update_config_accepts_legacy_default_names(self):
        mgr = MagicMock()
        client = TestClient(_get_app(mgr))

        payload = {
            "fps": 1.0,
            "resize_width": 640,
            "jpeg_quality": 75,
            "reconnect_delay": 9,
        }
        resp = client.patch("/config", json=payload)

        self.assertEqual(resp.status_code, 200)
        mgr.update_global_config.assert_called_once_with(
            default_fps=1.0,
            default_resize_width=640,
            default_jpeg_quality=75,
            default_reconnect_delay=9,
        )


class TestOpenAPISchemas(unittest.TestCase):
    """OpenAPI should expose only the clean public request fields."""

    def test_camera_request_schema_hides_legacy_motion_fields(self):
        app = _get_app(MagicMock())
        schemas = app.openapi()["components"]["schemas"]

        add_props = schemas["CameraAddRequest"]["properties"]
        update_props = schemas["CameraUpdateRequest"]["properties"]

        self.assertIn("motion", add_props)
        self.assertIn("motion", update_props)
        self.assertNotIn("motion_min_contour_area", add_props)
        self.assertNotIn("motion_threshold", add_props)
        self.assertNotIn("motion_blur_size", add_props)
        self.assertNotIn("motion_frames_to_average", add_props)
        self.assertNotIn("motion_min_duration", add_props)
        self.assertNotIn("motion_min_contour_area", update_props)
        self.assertNotIn("motion_threshold", update_props)
        self.assertNotIn("motion_blur_size", update_props)
        self.assertNotIn("motion_frames_to_average", update_props)
        self.assertNotIn("motion_min_duration", update_props)

    def test_global_config_schema_uses_default_field_names(self):
        app = _get_app(MagicMock())
        props = app.openapi()["components"]["schemas"]["GlobalConfigUpdate"]["properties"]

        self.assertIn("default_fps", props)
        self.assertIn("default_resize_width", props)
        self.assertIn("default_jpeg_quality", props)
        self.assertIn("default_reconnect_delay", props)
        self.assertNotIn("fps", props)
        self.assertNotIn("resize_width", props)
        self.assertNotIn("jpeg_quality", props)
        self.assertNotIn("reconnect_delay", props)
