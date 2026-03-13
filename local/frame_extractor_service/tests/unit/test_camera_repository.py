"""Tests for CameraConfigRepository — load/save with various scenarios."""
import json
import unittest
from unittest.mock import patch, MagicMock

from schemas import CameraConfig
from core.camera_config_repository import CameraConfigRepository


class TestCameraRepositoryLoad(unittest.TestCase):

    def setUp(self):
        self.repo = CameraConfigRepository("test_cameras.json")

    @patch("pathlib.Path.exists", return_value=False)
    def test_load_all_missing_file_returns_empty_list(self, mock_exists):
        result = self.repo.load_all()
        self.assertEqual(result, [])

    @patch("pathlib.Path.exists", return_value=True)
    @patch(
        "pathlib.Path.read_text",
        return_value='{"cameras": [{"id": "cam1", "rtsp": "rtsp://valid"}]}',
    )
    def test_load_all_valid_json_returns_camera_configs(self, mock_read, mock_exists):
        result = self.repo.load_all()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "cam1")
        self.assertEqual(result[0].rtsp, "rtsp://valid")

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="{corrupt json!!!")
    def test_load_all_corrupt_json_returns_empty_list(self, mock_read, mock_exists):
        result = self.repo.load_all()
        self.assertEqual(result, [])

    @patch("pathlib.Path.exists", return_value=True)
    @patch(
        "pathlib.Path.read_text",
        return_value='{"cameras": [{"rtsp": "rtsp://missing_id"}]}',
    )
    def test_load_all_missing_required_key_returns_empty_list(self, mock_read, mock_exists):
        result = self.repo.load_all()
        self.assertEqual(result, [])

    @patch("pathlib.Path.exists", return_value=True)
    @patch(
        "pathlib.Path.read_text",
        return_value='{"cameras": [{"id": "кириліця", "rtsp": "rtsp://utf8"}]}',
    )
    def test_load_all_utf8_names(self, mock_read, mock_exists):
        result = self.repo.load_all()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "кириліця")


class TestCameraRepositorySave(unittest.TestCase):

    def setUp(self):
        self.repo = CameraConfigRepository("test_cameras.json")

    @patch("pathlib.Path.write_text")
    def test_save_all_creates_file_with_valid_json(self, mock_write):
        cameras = [CameraConfig(id="c1", rtsp="rtsp://c1")]
        self.repo.save_all(cameras)

        mock_write.assert_called_once()
        written = mock_write.call_args[0][0]
        data = json.loads(written)
        self.assertIn("cameras", data)
        self.assertEqual(data["cameras"][0]["id"], "c1")

    @patch("pathlib.Path.write_text")
    def test_save_all_roundtrip_preserves_data(self, mock_write):
        cameras = [
            CameraConfig(id="c1", rtsp="rtsp://c1", fps=5.0, resize_width=640),
            CameraConfig(id="c2", rtsp="rtsp://c2"),
        ]
        self.repo.save_all(cameras)

        written = mock_write.call_args[0][0]
        data = json.loads(written)
        self.assertEqual(len(data["cameras"]), 2)
        self.assertEqual(data["cameras"][0]["fps"], 5.0)
        self.assertEqual(data["cameras"][0]["resize_width"], 640)

    @patch("pathlib.Path.write_text")
    def test_save_all_overwrite_previous(self, mock_write):
        self.repo.save_all([CameraConfig(id="old", rtsp="rtsp://old")])
        self.repo.save_all([CameraConfig(id="new", rtsp="rtsp://new")])
        self.assertEqual(mock_write.call_count, 2)
        last_written = mock_write.call_args[0][0]
        self.assertIn("new", last_written)

    @patch("pathlib.Path.write_text")
    def test_save_all_empty_list(self, mock_write):
        self.repo.save_all([])
        written = mock_write.call_args[0][0]
        data = json.loads(written)
        self.assertEqual(data["cameras"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
