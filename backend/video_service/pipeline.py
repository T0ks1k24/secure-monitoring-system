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


def load_zones(camera_id: int):
    if not os.path.exists(ZONES_FILE):
        return []

    with open(ZONES_FILE, "r") as f:
        data = json.load(f)

    return [
        Zone(**z)
        for z in data
        if z["camera_id"] == camera_id
    ]   

def save_zones_to_file(new_zones):
    existing = []

    if os.path.exists(ZONES_FILE):
        with open(ZONES_FILE, "r") as f:
            existing = json.load(f)

    camera_id = new_zones[0].camera_id if new_zones else None

    existing = [
        z for z in existing
        if z["camera_id"] != camera_id
    ]

    existing.extend([z.model_dump() for z in new_zones])

    with open(ZONES_FILE, "w") as f:
        json.dump(existing, f, indent=4)


class VideoPipeline:
    def __init__(self, video_path: str, camera_id: int):
        self.camera_id = camera_id
        self.video = VideoSource(video_path)
        self.detector = ObjectDetector()
        self.zones = load_zones(camera_id)

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
    
    def add_zone(self, zone_data):

        all_data = []
        if os.path.exists(ZONES_FILE):
            with open(ZONES_FILE, "r") as f:
                all_data = json.load(f)

        new_id = max([z["id"] for z in all_data], default=0) + 1

        polygon = [
            [int(point[0]), int(point[1])]
            for point in zone_data["polygon"]
        ]

        zone = Zone(
            id=new_id,
            camera_id = self.camera_id,
            name=zone_data["name"],
            polygon=polygon,
            forbidden_classes=zone_data.get("forbidden_classes", ["person"]),
        )

        self.zones.append(zone)

        save_zones_to_file(self.zones)

        self.zones = load_zones(self.camera_id)
        self.zone_engine = ZoneEngine(self.zones)

        

        return zone
