import cv2
import numpy as np
from typing import List, Dict, Tuple, Set

from config.settings import settings
from schemas.events import Zone, RiskLevel, SecurityEvent
from services.tracker import Track

# Color constants (BGR)
COLORS = {
    "NONE": (200, 200, 200),            # Gray
    RiskLevel.LOW: (0, 255, 0),         # Green
    RiskLevel.MEDIUM: (0, 255, 255),    # Yellow
    RiskLevel.HIGH: (0, 165, 255),      # Orange
    RiskLevel.CRITICAL: (0, 0, 255),    # Red
}

class DebugVisualizer:
    """
    Visualizes the AI pipeline processing: frames, zones, and tracks.
    Used for debugging purposes only.
    """
    
    def __init__(self):
        self._window_name = "AI Model Service Debug"
    
    def _draw_zones(self, frame: np.ndarray, zones: List[Zone]):
        """Draws zone polygons on the frame."""
        h, w = frame.shape[:2]
        
        for zone in zones:
            if not zone.enabled:
                continue
                
            # Convert normalized coordinates to pixels
            pts = np.array([[int(x * w), int(y * h)] for x, y in zone.polygon], np.int32)
            pts = pts.reshape((-1, 1, 2))
            
            # Draw polygon boundary
            color = (255, 0, 0) # Blue for zones
            cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)
            
            # Put zone name
            if len(pts) > 0:
                cv2.putText(
                    frame, 
                    zone.name, 
                    (pts[0][0][0], pts[0][0][1] - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, 
                    color, 
                    2
                )

    def _draw_tracks(
        self, 
        frame: np.ndarray, 
        tracks: List[Track], 
        events: List[SecurityEvent]
    ):
        """Draws bounding boxes, IDs, and risk info for tracked objects."""
        h, w = frame.shape[:2]
        
        # Build mapping from track_id to its highest risk event
        track_events = {}
        for event in events:
            if event.track_id:
                if event.track_id not in track_events or event.risk_level > track_events[event.track_id].risk_level:
                    track_events[event.track_id] = event

        for track in tracks:
            # Convert to pixels
            x1, y1 = int(track.bbox.x1 * w), int(track.bbox.y1 * h)
            x2, y2 = int(track.bbox.x2 * w), int(track.bbox.y2 * h)
            
            # Default to no risk
            risk_level = "NONE"
            event_text = ""
            
            if track.id in track_events:
                evt = track_events[track.id]
                risk_level = evt.risk_level
                event_text = f" [{evt.event_type.value}]"
            
            color = COLORS.get(risk_level, COLORS["NONE"])
            
            # Draw bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"ID:{track.id} {track.obj_class}{event_text}"
            
            # Text background
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - text_h - 4), (x1 + text_w, y1), color, -1)
            
            # Text
            text_color = (0, 0, 0) if risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM] else (255, 255, 255)
            cv2.putText(
                frame, 
                label, 
                (x1, y1 - 2), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.5, 
                text_color, 
                1
            )

    def show(
        self, 
        frame: np.ndarray, 
        zones: List[Zone], 
        tracks: List[Track],
        events: List[SecurityEvent]
    ):
        """Renders the debugging visualization on screen."""
        if not settings.DEBUG_VISUALIZE:
            return
            
        display_frame = frame.copy()
        
        self._draw_zones(display_frame, zones)
        self._draw_tracks(display_frame, tracks, events)
        
        cv2.imshow(self._window_name, display_frame)
        cv2.waitKey(1) # Refresh window, non-blocking

# Singleton instance
debug_visualizer = DebugVisualizer()
