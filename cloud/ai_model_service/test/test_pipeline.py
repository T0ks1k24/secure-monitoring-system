import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import numpy as np
import time

from schemas.events import DetectRequest, Zone, ZoneType, BoundingBox
from services.pipeline import AnalyzePipeline
from services.tracker import Track

@pytest.fixture
def mock_deps():
    with patch("services.pipeline.detector") as mock_detector, \
         patch("services.pipeline.tracker_registry") as mock_registry, \
         patch("services.pipeline.zone_manager") as mock_zone_manager, \
         patch("services.pipeline.risk_engine") as mock_risk_engine, \
         patch("services.pipeline.rabbitmq_service") as mock_rabbitmq_service, \
         patch("services.debug_visualizer.debug_visualizer") as mock_visualizer:
        
        # Setup mocks
        mock_tracker = MagicMock()
        mock_registry.get.return_value = mock_tracker
        mock_zone_manager.get_zones = AsyncMock(return_value=[])
        mock_rabbitmq_service.publish_events = AsyncMock(return_value=0)
        
        yield {
            "detector": mock_detector,
            "tracker": mock_tracker,
            "registry": mock_registry,
            "zone_manager": mock_zone_manager,
            "risk_engine": mock_risk_engine,
            "rabbitmq": mock_rabbitmq_service,
            "visualizer": mock_visualizer,
        }

@pytest.fixture
def pipeline():
    return AnalyzePipeline()

@pytest.mark.asyncio
async def test_process_no_detections(pipeline, mock_deps):
    mock_deps["detector"].detect.return_value = []
    mock_deps["tracker"].update.return_value = []
    mock_deps["risk_engine"].analyze.return_value = []
    
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    req = DetectRequest(camera_id="cam1")
    
    resp = await pipeline.process(frame, req)
    
    assert resp.camera_id == "cam1"
    assert len(resp.tracked_objects) == 0
    assert resp.events_published == 0
    assert resp.processing_time_ms > 0
    
    mock_deps["detector"].detect.assert_called_once_with(frame)
    mock_deps["tracker"].update.assert_called_once_with([], [])
    mock_deps["rabbitmq"].publish_events.assert_not_called()

@pytest.mark.asyncio
async def test_process_with_detections_and_events(pipeline, mock_deps):
    # Setup Detections
    bbox = BoundingBox(x1=0.1, y1=0.1, x2=0.2, y2=0.2)
    mock_deps["detector"].detect.return_value = [(bbox, "person", 0.9)]
    
    # Setup Tracker
    track = Track(bbox, "person", 0.9)
    track.id = 1
    mock_deps["tracker"].update.return_value = [track]
    
    # Setup Zones
    zone = Zone(
        id="z1", camera_id="cam1", name="Entrance",
        zone_type=ZoneType.RESTRICTED,
        polygon=[[0,0], [1,0], [1,1], [0,1]]
    )
    mock_deps["zone_manager"].get_zones = AsyncMock(return_value=[zone])
    mock_deps["zone_manager"].find_zones_for_object.return_value = [zone]
    
    # Setup Risk Engine
    from schemas.events import EventType, RiskLevel
    mock_event = MagicMock()
    mock_event.event_type = EventType.ZONE_INTRUSION
    mock_event.risk_level = RiskLevel.HIGH
    mock_event.track_id = 1
    mock_event.zone_name = "Entrance"
    mock_deps["risk_engine"].analyze.return_value = [mock_event]
    
    # Setup RabbitMQ
    mock_deps["rabbitmq"].publish_events = AsyncMock(return_value=1)
    
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    req = DetectRequest(camera_id="cam1", frame_timestamp=123.45)
    
    resp = await pipeline.process(frame, req)
    
    assert resp.camera_id == "cam1"
    assert resp.frame_timestamp == 123.45
    assert len(resp.tracked_objects) == 1
    assert resp.tracked_objects[0].track_id == 1
    assert resp.events_published == 1
    
    # Check that events were published
    mock_deps["rabbitmq"].publish_events.assert_called_once_with([mock_event])
