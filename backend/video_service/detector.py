from ultralytics import YOLO
from models import DetectionResult, BoundingBox


class ObjectDetector:
    def __init__(self):
        self.model = YOLO("yolov8n.pt")
        self.allowed_classes = ["person", "car", "truck"]

    def detect(self, frame):
        results = self.model(frame, conf=0.5, verbose=False)
        detections = []

        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                label = self.model.names[cls_id]

                if label not in self.allowed_classes:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])

                detections.append(
                    DetectionResult(
                        label=label,
                        bbox=BoundingBox(x=x1, y=y1, w=x2 - x1, h=y2 - y1),
                        confidence=float(box.conf[0]),
                    )
                )

        return detections
