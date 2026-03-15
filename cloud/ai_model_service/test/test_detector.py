import pytest
from unittest.mock import patch, MagicMock
import numpy as np

from config.settings import settings
from schemas.events import BoundingBox
from models.detector import YOLODetector, COCO_CLASS_MAP

@pytest.fixture
def detector():
    # Make a fresh instance for testing
    d = YOLODetector()
    return d

def test_initial_state(detector):
    assert detector.is_loaded is False
    assert detector._model is None

def test_load_success(detector):
    with patch("ultralytics.YOLO") as mock_yolo:
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        detector.load()
        
        assert detector.is_loaded is True
        mock_yolo.assert_called_once_with(settings.MODEL_PATH)
        mock_model.assert_called_once() # dummy inference

def test_detect_not_loaded(detector):
    with pytest.raises(RuntimeError, match="YOLO model not loaded"):
        detector.detect(np.zeros((10, 10, 3), dtype=np.uint8))

def test_detect_success(detector):
    with patch("ultralytics.YOLO") as mock_yolo:
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        detector.load()
        
        # Setup mock results
        mock_result = MagicMock()
        mock_box = MagicMock()
        mock_box.xyxy = np.array([[10.0, 20.0, 30.0, 40.0]]) # pixels
        mock_box.cls = np.array([0]) # person
        mock_box.conf = np.array([0.9])
        mock_result.boxes = [mock_box]
        
        mock_model.return_value = [mock_result]
        
        # 100x100 frame
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        detections = detector.detect(frame)
        
        assert len(detections) == 1
        bbox, cls_name, conf = detections[0]
        
        # Should be normalized dividing by width/height (100)
        assert bbox.x1 == 0.1
        assert bbox.y1 == 0.2
        assert bbox.x2 == 0.3
        assert bbox.y2 == 0.4
        
        assert cls_name == "person"
        assert conf == 0.9

def test_detect_unknown_class(detector):
    with patch("ultralytics.YOLO") as mock_yolo:
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        detector.load()
        
        mock_result = MagicMock()
        mock_box = MagicMock()
        mock_box.xyxy = np.array([[10.0, 20.0, 30.0, 40.0]])
        mock_box.cls = np.array([999]) # unknown class id
        mock_box.conf = np.array([0.5])
        mock_result.boxes = [mock_box]
        mock_model.return_value = [mock_result]
        
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        detections = detector.detect(frame)
        
        assert len(detections) == 1
        bbox, cls_name, conf = detections[0]
        assert cls_name == "class_999"
