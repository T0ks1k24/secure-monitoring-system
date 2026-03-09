"""
Тести для CameraManager.
Потребують: pip install pydantic pydantic-settings httpx
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio, json, tempfile, unittest
from unittest.mock import AsyncMock, MagicMock, patch

try:
    from schemas import CameraCreateRequest, CameraUpdateRequest, MotionConfigSchema
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False


def _make_manager(tmp_path=None):
    from camera_manager import CameraManager
    if tmp_path is None:
        f = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        f.close()
        tmp_path = f.name
    with patch("camera_manager.settings") as s:
        s.AI_SERVICE_URL = "http://ai/detect"
        s.AI_REQUEST_TIMEOUT = 5
        s.DEFAULT_FPS = 2.0
        s.DEFAULT_RESIZE_WIDTH = 640
        s.DEFAULT_JPEG_QUALITY = 80
        s.DEFAULT_RECONNECT_DELAY = 3
        s.CAMERAS_CONFIG_PATH = tmp_path
        mgr = CameraManager()
        mgr._config_path = __import__("pathlib").Path(tmp_path)
    return mgr, tmp_path

def _req(**kw):
    d = dict(id="cam1", rtsp="rtsp://fake/1", enabled=False)
    d.update(kw)
    return CameraCreateRequest(**d)


@unittest.skipUnless(DEPS_AVAILABLE, "pydantic not installed")
class TestAddCamera(unittest.TestCase):

    def test_returns_response(self):
        from schemas import CameraStatus
        mgr, _ = _make_manager()
        resp = mgr.add_camera(_req())
        self.assertEqual(resp.id, "cam1")
        self.assertEqual(resp.status, CameraStatus.STOPPED)

    def test_duplicate_raises(self):
        mgr, _ = _make_manager()
        mgr.add_camera(_req())
        with self.assertRaises(ValueError):
            mgr.add_camera(_req())

    def test_saves_to_file(self):
        mgr, path = _make_manager()
        mgr.add_camera(_req())
        data = json.loads(open(path).read())
        self.assertTrue(any(c["id"] == "cam1" for c in data["cameras"]))

    def test_add_multiple(self):
        mgr, _ = _make_manager()
        mgr.add_camera(_req(id="c1", rtsp="rtsp://1"))
        mgr.add_camera(_req(id="c2", rtsp="rtsp://2"))
        self.assertEqual(len(mgr.get_all_cameras()), 2)


@unittest.skipUnless(DEPS_AVAILABLE, "pydantic not installed")
class TestGetCamera(unittest.TestCase):

    def test_get_existing(self):
        mgr, _ = _make_manager()
        mgr.add_camera(_req())
        self.assertEqual(mgr.get_camera("cam1").id, "cam1")

    def test_get_nonexistent_raises(self):
        mgr, _ = _make_manager()
        with self.assertRaises(KeyError):
            mgr.get_camera("ghost")

    def test_get_all_empty(self):
        mgr, _ = _make_manager()
        self.assertEqual(mgr.get_all_cameras(), [])


@unittest.skipUnless(DEPS_AVAILABLE, "pydantic not installed")
class TestUpdateCamera(unittest.TestCase):

    def test_update_rtsp(self):
        mgr, _ = _make_manager()
        mgr.add_camera(_req())
        mgr.update_camera("cam1", CameraUpdateRequest(rtsp="rtsp://new"))
        self.assertEqual(mgr.get_camera("cam1").rtsp, "rtsp://new")

    def test_update_fps_changes_worker(self):
        mgr, _ = _make_manager()
        mgr.add_camera(_req())
        mgr.update_camera("cam1", CameraUpdateRequest(fps=15.0))
        self.assertEqual(mgr._workers["cam1"].fps, 15.0)

    def test_update_motion_config(self):
        mgr, _ = _make_manager()
        mgr.add_camera(_req())
        mgr.update_camera("cam1", CameraUpdateRequest(
            motion=MotionConfigSchema(cooldown_seconds=42.0)
        ))
        self.assertEqual(mgr._workers["cam1"]._motion.config.cooldown_seconds, 42.0)

    def test_update_nonexistent_raises(self):
        mgr, _ = _make_manager()
        with self.assertRaises(KeyError):
            mgr.update_camera("ghost", CameraUpdateRequest(fps=5.0))


@unittest.skipUnless(DEPS_AVAILABLE, "pydantic not installed")
class TestRemoveCamera(unittest.TestCase):

    def test_remove_existing(self):
        async def run():
            mgr, _ = _make_manager()
            mgr.add_camera(_req())
            await mgr.remove_camera("cam1")
            self.assertEqual(len(mgr.get_all_cameras()), 0)
        asyncio.run(run())

    def test_remove_nonexistent_raises(self):
        async def run():
            mgr, _ = _make_manager()
            with self.assertRaises(KeyError):
                await mgr.remove_camera("ghost")
        asyncio.run(run())

    def test_remove_saves_file(self):
        async def run():
            mgr, path = _make_manager()
            mgr.add_camera(_req(id="c1", rtsp="rtsp://1"))
            mgr.add_camera(_req(id="c2", rtsp="rtsp://2"))
            await mgr.remove_camera("c1")
            data = json.loads(open(path).read())
            ids = [c["id"] for c in data["cameras"]]
            self.assertNotIn("c1", ids)
            self.assertIn("c2", ids)
        asyncio.run(run())


@unittest.skipUnless(DEPS_AVAILABLE, "pydantic not installed")
class TestToResponse(unittest.TestCase):

    def test_has_all_motion_fields(self):
        mgr, _ = _make_manager()
        mgr.add_camera(_req())
        resp = mgr.get_camera("cam1")
        self.assertTrue(hasattr(resp, "frames_skipped"))
        self.assertTrue(hasattr(resp, "motion_events"))
        self.assertTrue(hasattr(resp, "motion_active"))
        self.assertTrue(hasattr(resp, "motion"))

    def test_stats_start_at_zero(self):
        mgr, _ = _make_manager()
        mgr.add_camera(_req())
        resp = mgr.get_camera("cam1")
        self.assertEqual(resp.frames_sent, 0)
        self.assertEqual(resp.frames_failed, 0)
        self.assertEqual(resp.frames_skipped, 0)
        self.assertEqual(resp.motion_events, 0)
        self.assertFalse(resp.motion_active)


@unittest.skipUnless(DEPS_AVAILABLE, "pydantic not installed")
class TestPersistence(unittest.TestCase):

    def test_load_from_file(self):
        async def run():
            f = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
            json.dump({"cameras": [{"id": "cam1", "rtsp": "rtsp://x", "enabled": False}]}, f)
            f.close()
            from camera_manager import CameraManager
            with patch("camera_manager.settings") as s:
                s.AI_SERVICE_URL = "http://ai/detect"
                s.AI_REQUEST_TIMEOUT = 5
                s.DEFAULT_FPS = 2.0
                s.DEFAULT_RESIZE_WIDTH = 640
                s.DEFAULT_JPEG_QUALITY = 80
                s.DEFAULT_RECONNECT_DELAY = 3
                s.CAMERAS_CONFIG_PATH = f.name
                mgr = CameraManager()
                mgr._config_path = __import__("pathlib").Path(f.name)
                await mgr.startup()
            self.assertIn("cam1", mgr._workers)
        asyncio.run(run())

    def test_missing_file_starts_empty(self):
        async def run():
            from camera_manager import CameraManager
            with patch("camera_manager.settings") as s:
                s.AI_SERVICE_URL = "http://ai/detect"
                s.AI_REQUEST_TIMEOUT = 5
                s.DEFAULT_FPS = 2.0
                s.DEFAULT_RESIZE_WIDTH = 640
                s.DEFAULT_JPEG_QUALITY = 80
                s.DEFAULT_RECONNECT_DELAY = 3
                s.CAMERAS_CONFIG_PATH = "/tmp/nonexistent_xyz_abc.json"
                mgr = CameraManager()
                mgr._config_path = __import__("pathlib").Path("/tmp/nonexistent_xyz_abc.json")
                await mgr.startup()
            self.assertEqual(len(mgr._workers), 0)
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
