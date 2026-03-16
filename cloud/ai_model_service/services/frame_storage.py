import os
import cv2
import logging
import numpy as np
from typing import Optional
from datetime import datetime
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)

class FrameStorageService:
    """
    Service for saving frames to the file system.
    """

    def save_frame(self, frame: np.ndarray, camera_id: str, timestamp: float) -> Optional[str]:
        """
        Saves a frame as a JPEG file.
        Returns the path to the saved file if successful, None otherwise.
        """
        try:
            base_path = Path(settings.FRAME_STORAGE_PATH)
            # Create directory for the camera if it doesn't exist
            cam_dir = base_path / str(camera_id)
            cam_dir.mkdir(parents=True, exist_ok=True)
            
            # Format timestamp for filename
            # Use ISO-like format for readability but filename friendly
            dt = datetime.fromtimestamp(timestamp)
            filename = f"{dt.strftime('%Y%m%d_%H%M%S')}_{dt.microsecond // 1000:03d}.jpg"
            file_path = cam_dir / filename
            
            # Save the image
            success = cv2.imwrite(str(file_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            if success:
                logger.debug(f"Saved frame for camera {camera_id} to {file_path}")
                return str(file_path)
            else:
                logger.error(f"Failed to write frame to {file_path}")
                return None
                
        except Exception as e:
            logger.exception(f"Error saving frame for camera {camera_id}: {e}")
            return None

# Singleton instance
frame_storage = FrameStorageService()
