import unittest
import os
from schemas import CameraConfig, MotionConfig
from core.sqlite_camera_repository import SQLiteCameraRepository

class TestSQLiteCameraRepository(unittest.TestCase):
    def setUp(self):
        self.db_url = "sqlite:///test_cameras.db"
        self.repo = SQLiteCameraRepository(self.db_url)

    def tearDown(self):
        if os.path.exists("test_cameras.db"):
            os.remove("test_cameras.db")

    def test_add_and_load_all(self):
        cam = CameraConfig(rtsp="rtsp://test", name="Test Cam")
        new_id = self.repo.add(cam)
        
        self.assertGreater(new_id, 0)
        cameras = self.repo.load_all()
        self.assertEqual(len(cameras), 1)
        self.assertEqual(cameras[0].id, new_id)
        self.assertEqual(cameras[0].name, "Test Cam")

    def test_update_camera(self):
        cam = CameraConfig(id=1, rtsp="rtsp://test", name="Test Cam")
        self.repo.add(cam)
        
        cam.name = "Updated Cam"
        cam.enabled = False
        self.repo.update(cam)
        
        cameras = self.repo.load_all()
        self.assertEqual(cameras[0].name, "Updated Cam")
        self.assertEqual(cameras[0].enabled, False)

    def test_delete_camera(self):
        cam = CameraConfig(id=1, rtsp="rtsp://test", name="Test Cam")
        self.repo.add(cam)
        
        self.repo.delete(1)
        
        cameras = self.repo.load_all()
        self.assertEqual(len(cameras), 0)

    def test_save_all(self):
        cameras = [
            CameraConfig(id=1, rtsp="rtsp://1"),
            CameraConfig(id=2, rtsp="rtsp://2")
        ]
        self.repo.save_all(cameras)
        
        loaded = self.repo.load_all()
        self.assertEqual(len(loaded), 2)

if __name__ == "__main__":
    unittest.main()
