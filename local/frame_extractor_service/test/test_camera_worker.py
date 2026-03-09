"""
Тести для CameraWorker.
Потребують: pip install pydantic pydantic-settings httpx
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio
import numpy as np
import unittest
from unittest.mock import AsyncMock, MagicMock

try:
    from schemas import CameraConfig, CameraStatus, MotionConfigSchema
    from camera_worker import CameraWorker, CameraStats, _schema_to_motion_config
    from ai_client import AIClient
    from motion_detector import MotionConfig
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False


def make_config(**kwargs):
    defaults = dict(id="cam_test", rtsp="rtsp://fake/stream",
                    fps=10.0, resize_width=0, jpeg_quality=80, enabled=True)
    defaults.update(kwargs)
    return CameraConfig(**defaults)

def make_worker(config=None, ai_client=None):
    if config is None:
        config = make_config()
    if ai_client is None:
        ai_client = MagicMock(spec=AIClient)
        ai_client.send_frame = AsyncMock(return_value={"status": "ok"})
    return CameraWorker(config=config, ai_client=ai_client,
                        global_fps=2.0, global_resize_width=640,
                        global_jpeg_quality=80, global_reconnect_delay=1)


@unittest.skipUnless(DEPS_AVAILABLE, "pydantic/httpx not installed")
class TestWorkerInit(unittest.TestCase):

    def test_uses_camera_fps(self):
        self.assertEqual(make_worker(make_config(fps=5.0)).fps, 5.0)

    def test_falls_back_to_global_fps(self):
        self.assertEqual(make_worker(make_config(fps=None)).fps, 2.0)

    def test_uses_camera_resize(self):
        self.assertEqual(make_worker(make_config(resize_width=320)).resize_width, 320)

    def test_falls_back_to_global_resize(self):
        self.assertEqual(make_worker(make_config(resize_width=None)).resize_width, 640)

    def test_uses_camera_jpeg(self):
        self.assertEqual(make_worker(make_config(jpeg_quality=50)).jpeg_quality, 50)

    def test_initial_status_stopped(self):
        self.assertEqual(make_worker().status, CameraStatus.STOPPED)

    def test_initial_stats_zero(self):
        w = make_worker()
        self.assertEqual(w.stats.frames_sent, 0)
        self.assertEqual(w.stats.frames_failed, 0)
        self.assertEqual(w.stats.frames_skipped, 0)

    def test_camera_id(self):
        self.assertEqual(make_worker(make_config(id="my_cam")).camera_id, "my_cam")


@unittest.skipUnless(DEPS_AVAILABLE, "pydantic/httpx not installed")
class TestUpdateParams(unittest.TestCase):

    def test_update_fps(self):
        w = make_worker()
        w.update_params(fps=15.0)
        self.assertEqual(w.fps, 15.0)

    def test_update_resize(self):
        w = make_worker()
        w.update_params(resize_width=1280)
        self.assertEqual(w.resize_width, 1280)

    def test_update_jpeg(self):
        w = make_worker()
        w.update_params(jpeg_quality=60)
        self.assertEqual(w.jpeg_quality, 60)

    def test_none_values_ignored(self):
        w = make_worker()
        orig = w.fps
        w.update_params(fps=None)
        self.assertEqual(w.fps, orig)

    def test_update_motion_schema(self):
        w = make_worker()
        w.update_params(motion_schema=MotionConfigSchema(cooldown_seconds=99.0))
        self.assertEqual(w._motion.config.cooldown_seconds, 99.0)

    def test_motion_none_ignored(self):
        w = make_worker()
        orig = w._motion.config.cooldown_seconds
        w.update_params(motion_schema=None)
        self.assertEqual(w._motion.config.cooldown_seconds, orig)


@unittest.skipUnless(DEPS_AVAILABLE, "pydantic/httpx not installed")
class TestStartStop(unittest.TestCase):

    def test_stop_sets_stop_event(self):
        async def run():
            w = make_worker()
            await w.stop()
            self.assertTrue(w._stop_event.is_set())
        asyncio.run(run())

    def test_stop_status_stopped(self):
        async def run():
            w = make_worker()
            await w.stop()
            self.assertEqual(w.status, CameraStatus.STOPPED)
        asyncio.run(run())

    def test_stop_without_task_safe(self):
        async def run():
            w = make_worker()
            self.assertIsNone(w._task)
            await w.stop()  # не кидає exception
        asyncio.run(run())

    def test_double_start_logs_warning(self):
        async def run():
            import logging
            from unittest.mock import patch
            w = make_worker()
            mock_task = MagicMock()
            mock_task.done.return_value = False
            w._task = mock_task
            with patch.object(logging.getLogger("camera_worker"), "warning") as mw:
                w.start()
                mw.assert_called_once()
        asyncio.run(run())


@unittest.skipUnless(DEPS_AVAILABLE, "pydantic/httpx not installed")
class TestStatusCallback(unittest.TestCase):

    def test_callback_called_on_change(self):
        async def run():
            cb = AsyncMock()
            w = make_worker()
            w._on_status_change = cb
            await w._set_status(CameraStatus.CONNECTING)
            cb.assert_called_once_with("cam_test", CameraStatus.CONNECTING)
        asyncio.run(run())

    def test_callback_not_called_if_same(self):
        async def run():
            cb = AsyncMock()
            w = make_worker()
            w._on_status_change = cb
            w._status = CameraStatus.STOPPED
            await w._set_status(CameraStatus.STOPPED)
            cb.assert_not_called()
        asyncio.run(run())


@unittest.skipUnless(DEPS_AVAILABLE, "pydantic/httpx not installed")
class TestSchemaToMotionConfig(unittest.TestCase):

    def test_all_fields(self):
        s = MotionConfigSchema(enabled=False, min_contour_area=1234,
            min_total_area=5678, min_solidity=0.75, min_consecutive_frames=4,
            cooldown_seconds=7.5, blur_size=15, diff_threshold=30, dilate_iterations=3)
        cfg = _schema_to_motion_config(s)
        self.assertFalse(cfg.enabled)
        self.assertEqual(cfg.min_contour_area, 1234)
        self.assertEqual(cfg.min_total_area, 5678)
        self.assertEqual(cfg.cooldown_seconds, 7.5)

    def test_default_schema(self):
        cfg = _schema_to_motion_config(MotionConfigSchema())
        self.assertIsInstance(cfg, MotionConfig)
        self.assertTrue(cfg.enabled)


if __name__ == "__main__":
    unittest.main()
