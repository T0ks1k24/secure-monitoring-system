"""
YOLO детектор — singleton, завантажується один раз при старті.
Підтримує динамічну зміну параметрів через update_settings().
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from config.settings import settings
from schemas.events import BoundingBox

logger = logging.getLogger(__name__)

# YOLO class_id → human-readable name (підмножина COCO)
COCO_CLASS_MAP: dict[int, str] = {
    0:  "person",
    1:  "bicycle",
    2:  "car",
    3:  "motorcycle",
    4:  "airplane",
    5:  "bus",
    7:  "truck",
    14: "bird",
    15: "cat",
    16: "dog",
    24: "backpack",
    26: "handbag",
    28: "suitcase",
    39: "bottle",
    43: "knife",
    67: "cell phone",
    73: "laptop",
}

# Класи що вважаються «зброєю» — завжди CRITICAL
WEAPON_CLASSES = {"knife", "gun", "pistol", "rifle"}
# Транспорт
VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle"}


class YOLODetector:
    """
    Обгортка над ultralytics YOLO.
    Singleton — один примірник на весь процес.
    """
    _instance: Optional["YOLODetector"] = None

    def __init__(self) -> None:
        self._model = None
        self._loaded = False
        self._load_time: float = 0.0

    @classmethod
    def get_instance(cls) -> "YOLODetector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self) -> None:
        """Завантажує модель. Викликається один раз при старті."""
        if self._loaded:
            return
        try:
            from ultralytics import YOLO
            path = settings.MODEL_PATH
            logger.info(f"Loading YOLO model: {path} on device={settings.DEVICE}")
            t0 = time.monotonic()
            self._model = YOLO(path)
            # Перший прогін для JIT warm-up
            dummy = np.zeros((settings.INFERENCE_IMG_SIZE, settings.INFERENCE_IMG_SIZE, 3), dtype=np.uint8)
            self._model(dummy, verbose=False)
            self._load_time = time.monotonic() - t0
            self._loaded = True
            logger.info(f"YOLO loaded in {self._load_time:.2f}s")
        except Exception:
            logger.exception("Failed to load YOLO model")
            raise

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def detect(
        self,
        frame: np.ndarray,
        confidence: Optional[float] = None,
        iou: Optional[float] = None,
        img_size: Optional[int] = None,
        max_det: Optional[int] = None,
    ) -> List[Tuple[BoundingBox, str, float]]:
        """
        Виконує детекцію на кадрі.

        Returns:
            List of (BoundingBox в нормалізованих координатах, class_name, confidence)
        """
        if not self._loaded or self._model is None:
            raise RuntimeError("YOLO model not loaded")

        conf = confidence or settings.DETECTION_CONFIDENCE
        nms_iou = iou or settings.DETECTION_IOU
        size = img_size or settings.INFERENCE_IMG_SIZE
        max_d = max_det or settings.MAX_DETECTIONS

        h, w = frame.shape[:2]

        results = self._model(
            frame,
            conf=conf,
            iou=nms_iou,
            imgsz=size,
            max_det=max_d,
            device=settings.DEVICE,
            verbose=False,
        )

        detections: List[Tuple[BoundingBox, str, float]] = []

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                # xyxy у пікселях → нормалізуємо
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                bbox = BoundingBox(
                    x1=x1 / w, y1=y1 / h,
                    x2=x2 / w, y2=y2 / h,
                )
                cls_id = int(box.cls[0])
                conf_val = float(box.conf[0])
                cls_name = COCO_CLASS_MAP.get(cls_id, f"class_{cls_id}")
                detections.append((bbox, cls_name, conf_val))

        return detections


# Module-level singleton
detector = YOLODetector.get_instance()
