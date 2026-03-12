import json
import logging
from pathlib import Path
from typing import List

from schemas.camera_config import CameraConfig

logger = logging.getLogger(__name__)

class CameraConfigRepository:
    """Repository for persisting camera configurations to disk."""
    
    def __init__(self, config_path: str):
        self._config_path = Path(config_path)

    def load_all(self) -> List[CameraConfig]:
        if not self._config_path.exists():
            logger.info("No config file at '%s', starting fresh", self._config_path)
            return []
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            return [CameraConfig(**cam) for cam in data.get("cameras", [])]
        except Exception as exc:
            logger.error("Failed to load cameras config: %s", exc)
            return []

    def save_all(self, cameras: List[CameraConfig]) -> None:
        try:
            data = [cam.model_dump() for cam in cameras]
            self._config_path.write_text(
                json.dumps({"cameras": data}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.error("Failed to save cameras config: %s", exc)
