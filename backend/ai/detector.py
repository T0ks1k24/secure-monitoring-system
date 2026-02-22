import base64
import numpy as np
import cv2
from typing import List, Dict

from .model import model

# CONFIG
CONF_THRESHOLD = 0.5
IMG_SIZE = 512      # 512


# DETECTION
def detect_frame(frame_base64: str) -> List[Dict]:

    try:
        # decode base64
        jpg_bytes = base64.b64decode(frame_base64)
        np_arr = np.frombuffer(jpg_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return []

        # YOLO inference
        results = model(
            frame,
            imgsz=IMG_SIZE,
            conf=CONF_THRESHOLD,
            verbose=False
        )

        detections = []

        for r in results:
            for box in r.boxes:

                cls = int(box.cls[0])

                # class 0 = person (COCO)
                if cls != 0:
                    continue

                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                detections.append({
                    "class": "person",
                    "confidence": round(conf, 3),
                    "bbox": [
                        round(x1, 2),
                        round(y1, 2),
                        round(x2, 2),
                        round(y2, 2)
                    ]
                })

        return detections

    except Exception as e:
        print("[AI] Detection error:", e)
        return []
