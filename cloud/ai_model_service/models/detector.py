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

# YOLO class_id → human-readable name (security-relevant subset of COCO)
# Відфільтровано: тільки людина, транспорт і тварини
COCO_CLASS_MAP: dict[int, str] = {
    # People
    0:  "person",
    # Vehicles
    1:  "bicycle",
    2:  "car",
    3:  "motorcycle",
    5:  "bus",
    7:  "truck",
    # Animals
    15: "cat",
    16: "dog",
    17: "horse",
    18: "sheep",
    19: "cow",
    20: "elephant",
    21: "bear",
}

# IDs для YOLO classes= фільтру — передається прямо в inference (швидше)
ALLOWED_CLASS_IDS: list[int] = list(COCO_CLASS_MAP.keys())

# Транспорт
VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle"}
# Тварини
ANIMAL_CLASSES = {"dog", "cat", "horse", "sheep", "cow", "elephant", "bear"}
# Зброя — для risk_engine (YOLO не детектує, але залишаємо для майбутнього)
WEAPON_CLASSES: set[str] = set()



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
            classes=ALLOWED_CLASS_IDS,  # фільтр на рівні NMS — тільки потрібні класи
            device=settings.DEVICE,
            verbose=False,
        )

        detections: List[Tuple[BoundingBox, str, float]] = []

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls[0])
                cls_name = COCO_CLASS_MAP.get(cls_id)
                if cls_name is None:
                    continue  # пропустити невідомий клас

                # xyxy у пікселях → нормалізуємо
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                bbox = BoundingBox(
                    x1=x1 / w, y1=y1 / h,
                    x2=x2 / w, y2=y2 / h,
                )
                conf_val = float(box.conf[0])
                detections.append((bbox, cls_name, conf_val))

        return detections



# Module-level singleton
detector = YOLODetector.get_instance()
