import pytest
from unittest.mock import patch, MagicMock

from config.settings import settings
from schemas.events import BoundingBox
from services.tracker import Track, CameraTracker, TrackerRegistry, _iou, _hungarian_match

# ── Track tests ───────────────────────────────────────────────────────────────

def test_track_init():
    bbox = BoundingBox(x1=0.1, y1=0.1, x2=0.2, y2=0.2)
    track = Track(bbox, "person", 0.9)
    
    assert track.obj_class == "person"
    assert track.confidence == 0.9
    assert track.age_frames == 1
    assert track.hits == 1
    assert track.misses == 0
    assert not track.is_confirmed  # needs settings.TRACKER_MIN_HITS
    
    # speed and direction initially zero/None
    assert track.speed == 0.0
    assert track.direction_degrees is None
    
    # trajectory has one point
    assert len(track.trajectory) == 1
    assert track.trajectory[0] == pytest.approx((0.15, 0.15)) # cx, cy

def test_track_update_and_predict():
    bbox1 = BoundingBox(x1=0.1, y1=0.1, x2=0.2, y2=0.2)
    track = Track(bbox1, "person", 0.9)
    
    # Update with new bbox moved by +0.1
    bbox2 = BoundingBox(x1=0.2, y1=0.2, x2=0.3, y2=0.3)
    track.update(bbox2, "person", 0.95)
    
    assert track.hits == 2
    assert track.age_frames == 2
    assert track.confidence == 0.95
    assert len(track.trajectory) == 2
    assert track.is_confirmed # Because TRACKER_MIN_HITS is usually 2
    
    # Predict next pos
    pred = track.predict()
    assert pred.cx > bbox2.cx # should predict moving in the same direction
    assert pred.cy > bbox2.cy

def test_track_direction_and_speed():
    bbox1 = BoundingBox(x1=0.1, y1=0.1, x2=0.2, y2=0.2)
    track = Track(bbox1, "person", 0.9)
    
    # Needs at least 3 points for direction
    track.update(BoundingBox(x1=0.1+0.01, y1=0.1, x2=0.2+0.01, y2=0.2), "person", 0.9)
    track.update(BoundingBox(x1=0.1+0.02, y1=0.1, x2=0.2+0.02, y2=0.2), "person", 0.9)
    
    # Moving strictly right along X axis -> 90 degrees
    dir_deg = track.direction_degrees
    assert dir_deg is not None
    assert abs(dir_deg - 90.0) < 1.0 # 90 degrees = right
    
    assert track.speed > 0.0

def test_track_zone_dwelling(monkeypatch):
    import time
    bbox = BoundingBox(x1=0.1, y1=0.1, x2=0.2, y2=0.2)
    track = Track(bbox, "person", 0.9)
    
    t_start = 1000.0
    monkeypatch.setattr(time, "monotonic", lambda: t_start)
    
    # Enter zone
    track.enter_zone("z1")
    
    # Fast forward 5 seconds
    monkeypatch.setattr(time, "monotonic", lambda: t_start + 5.0)
    assert track.get_dwell_seconds("z1") == 5.0
    
    # Exit zone
    track.exit_zone("z1")
    
    # Fast forward another 5 seconds
    monkeypatch.setattr(time, "monotonic", lambda: t_start + 10.0)
    # Shouldn't increase, stays at 5
    assert track.get_dwell_seconds("z1") == 5.0
    
    # Re-enter
    track.enter_zone("z1")
    monkeypatch.setattr(time, "monotonic", lambda: t_start + 12.0)
    # 5.0 from before + 2.0 new = 7.0
    assert track.get_dwell_seconds("z1") == 7.0

# ── CameraTracker tests ───────────────────────────────────────────────────────

def test_iou():
    b1 = BoundingBox(x1=0, y1=0, x2=10, y2=10) # area 100
    b2 = BoundingBox(x1=5, y1=5, x2=15, y2=15) # area 100
    # inter = 5x5 = 25. union = 100+100-25 = 175. iou = 25/175 = 1/7 ~= 0.1428
    iou_val = _iou(b1, b2)
    assert 0.14 < iou_val < 0.15
    
    b3 = BoundingBox(x1=20, y1=20, x2=30, y2=30)
    assert _iou(b1, b3) == 0.0

def test_hungarian_match():
    # Helper to create track
    t1 = Track(BoundingBox(x1=0, y1=0, x2=10, y2=10), "person", 0.9)
    t2 = Track(BoundingBox(x1=20, y1=20, x2=30, y2=30), "car", 0.9)
    
    dets = [
        (BoundingBox(x1=22, y1=22, x2=32, y2=32), "car", 0.95),  # Matches t2
        (BoundingBox(x1=50, y1=50, x2=60, y2=60), "person", 0.8), # Unmatched
    ]
    
    matched, unmatched_t, unmatched_d = _hungarian_match([t1, t2], dets, iou_threshold=0.3)
    
    assert len(matched) == 1
    assert matched[0] == (1, 0) # t2 (idx=1) matched with first det (idx=0)
    assert unmatched_t == [0]   # t1 didn't match
    assert unmatched_d == [1]   # 2nd det didn't match

def test_camera_tracker_lifecycle():
    tracker = CameraTracker("cam1", fps=10.0)
    
    # Frame 1: One detection
    dets1 = [(BoundingBox(x1=0.1, y1=0.1, x2=0.2, y2=0.2), "person", 0.9)]
    confirmed1 = tracker.update(dets1, ["z1"])
    assert len(confirmed1) == 0 # min_hits not reached
    assert len(tracker._tracks) == 1
    track_id = tracker._tracks[0].id
    
    # Frame 2: Same object
    dets2 = [(BoundingBox(x1=0.11, y1=0.11, x2=0.21, y2=0.21), "person", 0.9)]
    confirmed2 = tracker.update(dets2, ["z1"])
    assert len(confirmed2) == 1
    assert confirmed2[0].id == track_id
    
    # Frame 3: Object missing
    confirmed3 = tracker.update([], ["z1"])
    assert len(confirmed3) == 1 # still returned because it was confirmed and within max_age
    assert tracker._tracks[0].misses == 1
    
    # Get Zone events
    events = tracker.get_zone_events(confirmed3, {track_id: {"z1"}})
    assert track_id in events
    entered, exited = events[track_id]
    assert "z1" in entered
    assert len(exited) == 0
    
    # Next frame, same zone
    events2 = tracker.get_zone_events(confirmed3, {track_id: {"z1"}})
    assert len(events2) == 0 # No change
    
    # Next frame, object leaves zone
    events3 = tracker.get_zone_events(confirmed3, {track_id: set()})
    assert track_id in events3
    entered3, exited3 = events3[track_id]
    assert len(entered3) == 0
    assert "z1" in exited3

def test_tracker_registry():
    registry = TrackerRegistry()
    
    t1 = registry.get("cam1")
    t1_again = registry.get("cam1")
    assert t1 is t1_again
    
    t2 = registry.get("cam2")
    assert registry.count == 2
    
    registry.remove("cam1")
    assert registry.count == 1
