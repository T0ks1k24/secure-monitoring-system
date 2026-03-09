"""
Тести для Pydantic schemas.
Потребують: pip install pydantic pydantic-settings
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import unittest

try:
    from schemas import (
        CameraConfig, CameraCreateRequest, CameraUpdateRequest,
        MotionConfigSchema, CameraStatus,
    )
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


@unittest.skipUnless(PYDANTIC_AVAILABLE, "pydantic not installed")
class TestMotionConfigSchema(unittest.TestCase):

    def test_defaults(self):
        m = MotionConfigSchema()
        self.assertTrue(m.enabled)
        self.assertEqual(m.min_contour_area, 4000)
        self.assertEqual(m.min_total_area, 6000)
        self.assertAlmostEqual(m.min_solidity, 0.4)
        self.assertEqual(m.min_consecutive_frames, 2)
        self.assertEqual(m.cooldown_seconds, 10.0)
        self.assertEqual(m.blur_size, 21)
        self.assertEqual(m.diff_threshold, 25)
        self.assertEqual(m.dilate_iterations, 2)

    def _raises(self, **kwargs):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            MotionConfigSchema(**kwargs)

    def test_min_contour_area_ge_100(self):     self._raises(min_contour_area=50)
    def test_min_solidity_below_min(self):      self._raises(min_solidity=0.05)
    def test_min_solidity_above_max(self):      self._raises(min_solidity=1.5)
    def test_min_consecutive_frames_ge_1(self): self._raises(min_consecutive_frames=0)
    def test_min_consecutive_frames_le_10(self):self._raises(min_consecutive_frames=11)
    def test_diff_threshold_ge_1(self):         self._raises(diff_threshold=0)
    def test_diff_threshold_le_255(self):       self._raises(diff_threshold=256)
    def test_dilate_iterations_le_5(self):      self._raises(dilate_iterations=6)


@unittest.skipUnless(PYDANTIC_AVAILABLE, "pydantic not installed")
class TestCameraConfig(unittest.TestCase):

    def test_minimal_config(self):
        c = CameraConfig(id="c1", rtsp="rtsp://x")
        self.assertIsNone(c.fps)
        self.assertTrue(c.enabled)
        self.assertIsInstance(c.motion, MotionConfigSchema)

    def test_motion_default_cooldown(self):
        c = CameraConfig(id="c1", rtsp="rtsp://x")
        self.assertEqual(c.motion.cooldown_seconds, 10.0)

    def test_full_config(self):
        c = CameraConfig(id="c2", rtsp="rtsp://h", fps=5.0,
                          resize_width=640, jpeg_quality=70, enabled=False)
        self.assertEqual(c.fps, 5.0)
        self.assertFalse(c.enabled)


@unittest.skipUnless(PYDANTIC_AVAILABLE, "pydantic not installed")
class TestCameraCreateRequest(unittest.TestCase):

    def _raises(self, **kwargs):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            CameraCreateRequest(id="x", rtsp="rtsp://x", **kwargs)

    def test_fps_too_low(self):      self._raises(fps=0.05)
    def test_fps_too_high(self):     self._raises(fps=31.0)
    def test_jpeg_zero(self):        self._raises(jpeg_quality=0)
    def test_jpeg_over_100(self):    self._raises(jpeg_quality=101)
    def test_resize_negative(self):  self._raises(resize_width=-1)

    def test_valid_request(self):
        req = CameraCreateRequest(id="cam1", rtsp="rtsp://h", fps=5.0)
        self.assertEqual(req.id, "cam1")

    def test_default_motion_attached(self):
        req = CameraCreateRequest(id="c", rtsp="rtsp://x")
        self.assertIsInstance(req.motion, MotionConfigSchema)


@unittest.skipUnless(PYDANTIC_AVAILABLE, "pydantic not installed")
class TestCameraUpdateRequest(unittest.TestCase):

    def test_all_optional(self):
        req = CameraUpdateRequest()
        self.assertIsNone(req.rtsp)
        self.assertIsNone(req.fps)
        self.assertIsNone(req.motion)

    def test_dump_exclude_none(self):
        req = CameraUpdateRequest(fps=5.0)
        d = req.model_dump(exclude_none=True)
        self.assertIn("fps", d)
        self.assertNotIn("rtsp", d)


@unittest.skipUnless(PYDANTIC_AVAILABLE, "pydantic not installed")
class TestCameraStatus(unittest.TestCase):

    def test_values(self):
        self.assertEqual(CameraStatus.RUNNING, "running")
        self.assertEqual(CameraStatus.STOPPED, "stopped")
        self.assertEqual(CameraStatus.CONNECTING, "connecting")
        self.assertEqual(CameraStatus.ERROR, "error")


if __name__ == "__main__":
    unittest.main()
