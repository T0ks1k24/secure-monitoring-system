import os
import cv2
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from services.pipeline import pipeline
from schemas.events import DetectRequest, Zone
from config.settings import settings

@pytest.fixture
def mock_detector():
    with patch("services.pipeline.detector") as m:
        m.detect.return_value = [] # No detections for simplicity
        m.is_loaded = True
        yield m

@pytest.fixture
def mock_zone_manager():
    with patch("services.pipeline.zone_manager") as m:
        m.get_zones.return_value = MagicMock(__await__=MagicMock(return_value=iter([])))
        m.get_zones.side_effect = None
        # Better way for AsyncMock:
        from unittest.mock import AsyncMock
        m.get_zones = AsyncMock(return_value=[])
        m.find_zones_for_object.return_value = []
        yield m

@pytest.fixture
def temp_storage(tmp_path):
    storage_path = tmp_path / "test_frames"
    storage_path.mkdir()
    old_path = settings.FRAME_STORAGE_PATH
    old_save = settings.SAVE_PROCESSED_FRAMES
    
    settings.FRAME_STORAGE_PATH = str(storage_path)
    settings.SAVE_PROCESSED_FRAMES = True
    
    yield storage_path
    
    settings.FRAME_STORAGE_PATH = old_path
    settings.SAVE_PROCESSED_FRAMES = old_save

@pytest.mark.asyncio
async def test_pipeline_saves_frame(mock_detector, mock_zone_manager, temp_storage):
    # Prepare a dummy frame (black image)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    request = DetectRequest(
        camera_id="test_cam_1",
        frame_timestamp=1710590000.0,
        stream_fps=10.0
    )
    
    # Process through pipeline
    await pipeline.process(frame, request)
    
    # Check if frame was saved
    cam_dir = temp_storage / "test_cam_1"
    assert cam_dir.exists()
    
    files = list(cam_dir.glob("*.jpg"))
    assert len(files) == 1
    
    # Verify it's a valid image
    saved_frame = cv2.imread(str(files[0]))
    assert saved_frame is not None
    assert saved_frame.shape == (480, 640, 3)
