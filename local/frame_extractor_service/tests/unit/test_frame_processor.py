"""Tests for MotionDetectorProcessor — resize logic and update_config."""
import unittest
from unittest.mock import patch

import numpy as np

from detection.motion_detector_processor import MotionDetectorProcessor
from schemas import MotionConfig


class TestFrameProcessorResize(unittest.TestCase):
    """Test suite for frame resizing in MotionDetectorProcessor."""

    def setUp(self):
        self.config = MotionConfig(enabled=False)  # disable motion for resize tests
        self.processor = MotionDetectorProcessor(self.config, resize_width=100)

    @patch("detection.motion_detector_processor.cv2.resize")
    def test_no_resize_when_width_is_zero(self, mock_resize):
        self.processor.resize_width = 0
        frame = np.zeros((100, 200, 3), dtype=np.uint8)

        should_send, result = self.processor.process(frame, 0.0)

        mock_resize.assert_not_called()
        self.assertTrue(should_send)  # motion disabled → always True
        self.assertIs(result, frame)

    @patch("detection.motion_detector_processor.cv2.resize")
    def test_resize_when_width_differs(self, mock_resize):
        resized = np.zeros((50, 100, 3), dtype=np.uint8)
        mock_resize.return_value = resized
        frame = np.zeros((100, 200, 3), dtype=np.uint8)

        _, _ = self.processor.process(frame, 0.0)

        mock_resize.assert_called_once()
        # Check dimensions: target is (100, 50) because aspect ratio 200:100 → 100:50
        call_args = mock_resize.call_args
        self.assertEqual(call_args[0][1], (100, 50))  # (width, height)

    @patch("detection.motion_detector_processor.cv2.resize")
    def test_no_resize_when_width_already_matches(self, mock_resize):
        frame = np.zeros((50, 100, 3), dtype=np.uint8)  # width=100 matches resize_width=100

        _, _ = self.processor.process(frame, 0.0)

        mock_resize.assert_not_called()

    @patch("detection.motion_detector_processor.cv2.resize")
    def test_preserves_aspect_ratio(self, mock_resize):
        mock_resize.return_value = np.zeros((75, 200, 3), dtype=np.uint8)
        self.processor.resize_width = 200
        frame = np.zeros((300, 800, 3), dtype=np.uint8)  # 800x300 → 200x75

        self.processor.process(frame, 0.0)

        call_args = mock_resize.call_args
        self.assertEqual(call_args[0][1], (200, 75))


class TestFrameProcessorUpdateConfig(unittest.TestCase):
    """Test suite for updating MotionDetectorProcessor configuration."""

    def test_update_config_changes_resize_width(self):
        config = MotionConfig(enabled=False)
        proc = MotionDetectorProcessor(config, resize_width=640)

        proc.update_config(resize_width=320)

        self.assertEqual(proc.resize_width, 320)

    def test_update_config_changes_motion_config(self):
        config = MotionConfig(enabled=True, min_contour_area=500)
        proc = MotionDetectorProcessor(config, resize_width=640)

        new_motion = MotionConfig(enabled=True, min_contour_area=9000)
        proc.update_config(motion=new_motion)

        self.assertEqual(proc.motion_config_schema, new_motion)
        self.assertEqual(proc._motion_detector.config.min_contour_area, 9000)  # pylint: disable=protected-access

    def test_update_config_none_values_do_not_change(self):
        config = MotionConfig(enabled=True)
        proc = MotionDetectorProcessor(config, resize_width=640)

        proc.update_config(resize_width=None, motion=None)

        self.assertEqual(proc.resize_width, 640)
        self.assertEqual(proc.motion_config_schema, config)


if __name__ == "__main__":
    unittest.main(verbosity=2)
