"""Unit tests for Pydantic schema refactor logic."""
import unittest
from schemas import CameraUpdateRequest, MotionUpdateRequest, MotionConfig

class TestSchemaRefactor(unittest.TestCase):
    """Test suite for validating schema updates and validators."""
    def test_motion_update_request_partial(self):
        """Verify that providing only one field works in MotionUpdateRequest."""
        req = MotionUpdateRequest(min_contour_area=999)
        self.assertEqual(req.min_contour_area, 999)
        self.assertIsNone(req.enabled)

    def test_blur_size_validator_odd(self):
        """Verify the blur_size validator for odd numbers."""
        # Valid odd number
        mc = MotionConfig(blur_size=23)
        self.assertEqual(mc.blur_size, 23)

        # Invalid even number
        with self.assertRaises(ValueError):
            MotionConfig(blur_size=22)

    def test_blur_size_validator_partial_update(self):
        """Verify the blur_size validator in partial updates."""
        # Valid odd number in partial update
        mur = MotionUpdateRequest(blur_size=5)
        self.assertEqual(mur.blur_size, 5)

        # Invalid even number in partial update
        with self.assertRaises(ValueError):
            MotionUpdateRequest(blur_size=4)

    def test_camera_update_request_structure(self):
        """Verify CameraUpdateRequest can handle partial motion updates."""
        req = CameraUpdateRequest(motion=MotionUpdateRequest(min_total_area=123))
        self.assertEqual(req.motion.min_total_area, 123)
        self.assertIsNone(req.fps)
