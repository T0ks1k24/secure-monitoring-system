"""Tests for CameraManager — startup, shutdown, CRUD, control, queries, global config."""
import unittest
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from schemas import (
    CameraAddRequest,
    CameraConfig,
    CameraStatusResponse,
    CameraUpdateRequest,
    MotionUpdateRequest,
)
from schemas import MotionConfig
from core.camera_manager import CameraManager
from core.camera_stats import CameraStats
from config import Settings


def _make_mock_worker(cam_id: int = 1, enabled: bool = True) -> MagicMock:
    """Create a MagicMock simulating a CameraWorker."""
    w = MagicMock()
    w.config = CameraConfig(id=cam_id, rtsp="rtsp://test", enabled=enabled)
    w.fps = 2.0
    w.stats = CameraStats()
    w.status = "stopped"
    w.get_processor_stats.return_value = {
        "motion_detected": False,
        "total_motion_events": 0,
        "consecutive_frames": 0,
    }
    w.stop = AsyncMock()
    return w


class TestCameraManagerStartup(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.factory = MagicMock()
        self.repo = MagicMock()
        self.ai_client = AsyncMock()
        self.settings = Settings(
            _env_file=None,
        )
        self.manager = CameraManager(
            worker_factory=self.factory,
            repository=self.repo,
            ai_client=self.ai_client,
            settings=self.settings,
        )

    async def test_startup_starts_enabled_cameras_only(self):
        enabled = CameraConfig(id=1, rtsp="rtsp://e1", enabled=True)
        disabled = CameraConfig(id=2, rtsp="rtsp://d1", enabled=False)
        self.repo.load_all.return_value = [enabled, disabled]

        w_enabled = _make_mock_worker(1)
        w_disabled = _make_mock_worker(2, enabled=False)
        self.factory.create_worker.side_effect = [w_enabled, w_disabled]

        await self.manager.startup()

        w_enabled.start.assert_called_once()
        w_disabled.start.assert_not_called()
        self.assertEqual(len(self.manager._workers), 2)

    async def test_startup_with_no_cameras(self):
        self.repo.load_all.return_value = []
        await self.manager.startup()
        self.assertEqual(len(self.manager._workers), 0)


class TestCameraManagerShutdown(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.factory = MagicMock()
        self.repo = MagicMock()
        self.ai_client = AsyncMock()
        self.settings = Settings(_env_file=None, CAMERAS_CONFIG_PATH="/dev/null")
        self.manager = CameraManager(self.factory, self.repo, self.ai_client, self.settings)

    async def test_shutdown_stops_all_workers_and_closes_client(self):
        w1 = _make_mock_worker(1)
        w2 = _make_mock_worker(2)
        self.manager._workers = {1: w1, 2: w2}

        await self.manager.shutdown()

        w1.stop.assert_awaited_once()
        w2.stop.assert_awaited_once()
        self.ai_client.aclose.assert_awaited_once()


class TestCameraManagerAdd(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.factory = MagicMock()
        self.repo = MagicMock()
        self.ai_client = AsyncMock()
        self.settings = Settings(_env_file=None)
        self.manager = CameraManager(self.factory, self.repo, self.ai_client, self.settings)

    def test_add_camera_success_and_starts_when_enabled(self):
        req = CameraAddRequest(rtsp="rtsp://new1")
        self.repo.add.return_value = 10
        w = _make_mock_worker(10)
        self.factory.create_worker.return_value = w

        result = self.manager.add_camera(req)

        self.assertEqual(result.id, 10)
        w.start.assert_called_once()
        self.repo.add.assert_called_once()

    def test_add_camera_not_started_when_disabled(self):
        req = CameraAddRequest(rtsp="rtsp://new2", enabled=False)
        self.repo.add.return_value = 20
        w = _make_mock_worker(20, enabled=False)
        self.factory.create_worker.return_value = w

        result = self.manager.add_camera(req)

        self.assertEqual(result.id, 20)
        w.start.assert_not_called()
        self.repo.add.assert_called_once()


class TestCameraManagerUpdate(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.factory = MagicMock()
        self.repo = MagicMock()
        self.ai_client = AsyncMock()
        self.settings = Settings(_env_file=None)
        self.manager = CameraManager(self.factory, self.repo, self.ai_client, self.settings)

    def test_update_camera_fps_and_resize_width(self):
        w = _make_mock_worker(1)
        self.manager._workers[1] = w

        req = CameraUpdateRequest(fps=5.0, resize_width=800)
        self.manager.update_camera(1, req)

        w.update_params.assert_called_once_with(
            fps=5.0, resize_width=800, jpeg_quality=None, motion=None,
        )
        self.repo.update.assert_called_once()

    def test_update_camera_with_motion_config(self):
        w = _make_mock_worker(1)
        self.manager._workers[1] = w
        # Initial area is 4000 (default)
        new_motion = MotionUpdateRequest(min_contour_area=9000)

        req = CameraUpdateRequest(motion=new_motion)
        self.manager.update_camera(1, req)

        self.assertEqual(w.config.motion.min_contour_area, 9000)
        self.assertEqual(w.config.motion.enabled, True)  # Should remain True (default)

    def test_update_camera_unknown_raises_key_error(self):
        req = CameraUpdateRequest(fps=1.0)
        with self.assertRaises(KeyError):
            self.manager.update_camera(999, req)


class TestCameraManagerRemove(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.factory = MagicMock()
        self.repo = MagicMock()
        self.ai_client = AsyncMock()
        self.settings = Settings(_env_file=None)
        self.manager = CameraManager(self.factory, self.repo, self.ai_client, self.settings)

    async def test_remove_camera_success(self):
        w = _make_mock_worker(1)
        self.manager._workers[1] = w

        await self.manager.remove_camera(1)

        w.stop.assert_awaited_once()
        self.assertNotIn(1, self.manager._workers)
        self.repo.delete.assert_called_once_with(1)

    async def test_remove_camera_unknown_raises_key_error(self):
        with self.assertRaises(KeyError):
            await self.manager.remove_camera(999)


class TestCameraManagerStartStop(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.factory = MagicMock()
        self.repo = MagicMock()
        self.ai_client = AsyncMock()
        self.settings = Settings(_env_file=None)
        self.manager = CameraManager(self.factory, self.repo, self.ai_client, self.settings)

    def test_start_camera_success(self):
        w = _make_mock_worker(1)
        self.manager._workers[1] = w

        result = self.manager.start_camera(1)
        w.start.assert_called_once()
        self.assertTrue(w.config.enabled)

    def test_start_camera_unknown_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.manager.start_camera(999)

    async def test_stop_camera_success(self):
        w = _make_mock_worker(1)
        self.manager._workers[1] = w

        result = await self.manager.stop_camera(1)
        w.stop.assert_awaited_once()
        self.assertFalse(w.config.enabled)

    async def test_stop_camera_unknown_raises_key_error(self):
        with self.assertRaises(KeyError):
            await self.manager.stop_camera(999)


class TestCameraManagerQueries(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.factory = MagicMock()
        self.repo = MagicMock()
        self.ai_client = AsyncMock()
        self.settings = Settings(_env_file=None)
        self.manager = CameraManager(self.factory, self.repo, self.ai_client, self.settings)

    def test_get_all_returns_list_of_responses(self):
        w1 = _make_mock_worker(1)
        w2 = _make_mock_worker(2)
        self.manager._workers = {1: w1, 2: w2}

        result = self.manager.get_all()
        self.assertEqual(len(result), 2)

    def test_get_one_returns_response(self):
        w = _make_mock_worker(1)
        self.manager._workers[1] = w

        result = self.manager.get_one(1)
        self.assertEqual(result.id, 1)

    def test_get_one_unknown_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.manager.get_one(999)


class TestCameraManagerGlobalConfig(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.factory = MagicMock()
        self.repo = MagicMock()
        self.ai_client = MagicMock()
        self.settings = Settings(_env_file=None)
        self.manager = CameraManager(self.factory, self.repo, self.ai_client, self.settings)

    def test_update_global_config_changes_ai_url(self):
        self.manager.update_global_config(ai_service_url="http://new-ai")
        self.ai_client.update_endpoint.assert_called_once_with("http://new-ai")
        self.assertEqual(self.settings.AI_SERVICE_URL, "http://new-ai")

    def test_update_global_config_does_not_call_update_endpoint_when_url_is_none(self):
        self.manager.update_global_config(default_fps=5.0)
        self.ai_client.update_endpoint.assert_not_called()
        self.assertEqual(self.settings.DEFAULT_FPS, 5.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
