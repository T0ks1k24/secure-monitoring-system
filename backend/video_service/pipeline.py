import cv2
import time
from datetime import datetime

from video_source import VideoSource
from detector import ObjectDetector
from zone_engine import ZoneEngine
from zone_models import Zone
import json
import os


ZONES_FILE = "zones.json"


def load_zones():
    if not os.path.exists(ZONES_FILE):
        return []

    with open(ZONES_FILE, "r") as f:
        data = json.load(f)

    return [Zone(**z) for z in data]


class VideoPipeline:
    def __init__(self, video_path: str):
        self.video = VideoSource(video_path)
        self.detector = ObjectDetector()
        self.zones = load_zones()
        self.zone_engine = ZoneEngine(self.zones)

        self.person_counter = 0

    def events(self):
        """
        Generator of semantic events (NOT frames)
        """
        while True:
            frame = self.video.get_frame()
            if frame is None:
                break

            detections = self.detector.detect(frame)

            for det in detections:
                if det.label == "person":
                    self.person_counter += 1

                zone_hits = self.zone_engine.check(det)

                if zone_hits:
                    yield {
                        "timestamp": datetime.utcnow().isoformat(),
                        "event": "ZONE_VIOLATION",
                        "object": det.label,
                        "confidence": det.confidence,
                        "zones": zone_hits,
                    }

            time.sleep(0.05)

    def risk_level(self):
        if self.person_counter > 10:
            return "HIGH"
        elif self.person_counter > 0:
            return "MEDIUM"
        return "LOW"

    def video_stream(self):
        """
        MJPEG stream generator
        """
        while True:
            frame = self.video.get_frame()
            if frame is None:
                break

            detections = self.detector.detect(frame)

            for det in detections:
                x, y, w, h = (
                    det.bbox.x,
                    det.bbox.y,
                    det.bbox.w,
                    det.bbox.h,
                )
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            ret, jpeg = cv2.imencode(".jpg", frame)
            if not ret:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
            )

            time.sleep(0.03)
