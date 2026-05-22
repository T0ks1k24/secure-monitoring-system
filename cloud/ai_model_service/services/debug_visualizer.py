import cv2
import numpy as np
from typing import List

from config.settings import settings
from schemas.events import Zone, SecurityEvent
from services.tracker import Track
from services.visual_renderer import visual_renderer

class DebugVisualizer:
    """
    Visualizes the AI pipeline processing: frames, zones, and tracks.
    Used for debugging purposes only. Utilizes VisualRenderer for drawing.
    """
    
    def __init__(self):
        self._window_name = "AI Model Service Debug"
    
    def show(
        self, 
        frame: np.ndarray,
        camera_id: str,
        zones: List[Zone], 
        tracks: List[Track],
        events: List[SecurityEvent]
    ):
        """Renders the debugging visualization on screen."""
        if not settings.DEBUG_VISUALIZE:
            return
            
        display_frame = visual_renderer.draw_overlays(
            frame, camera_id, zones, tracks, events
        )
        
        cv2.imshow(self._window_name, display_frame)
        cv2.waitKey(1) # Refresh window, non-blocking

# Singleton instance
debug_visualizer = DebugVisualizer()
