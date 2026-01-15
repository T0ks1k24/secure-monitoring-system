import cv2
import numpy as np
import json
import os

from video_source import VideoSource
from detector import ObjectDetector
from zone_models import Zone
from zone_engine import ZoneEngine
from zone_drawer import ZoneDrawer


# ================== CONFIG ==================
VIDEO_PATH = "../video/test_2.mp4"
ZONES_FILE = "zones.json"


# ================== ZONE STORAGE ==================
def load_zones():
    if not os.path.exists(ZONES_FILE):
        return []

    with open(ZONES_FILE, "r") as f:
        data = json.load(f)

    return [Zone(**z) for z in data]


def save_zones(zones):
    with open(ZONES_FILE, "w") as f:
        json.dump([z.model_dump() for z in zones], f, indent=4)


# ================== INIT ==================
video = VideoSource(VIDEO_PATH)
detector = ObjectDetector()

zone_drawer = ZoneDrawer()
zones = load_zones()
zone_engine = ZoneEngine(zones=zones)

cv2.namedWindow("Video Analytics")
cv2.setMouseCallback("Video Analytics", zone_drawer.mouse_callback)

print("INSTRUCTIONS:")
print(" - Left click: add zone point")
print(" - ENTER: save zone")
print(" - Q / ESC: exit")


# ================== MAIN LOOP ==================
while True:
    frame = video.get_frame()
    if frame is None:
        break

    detections = detector.detect(frame)

    # ===== DRAW SAVED ZONES =====
    for zone in zones:
        pts = np.array(zone.polygon, np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], True, (0, 0, 255), 2)

    # ===== DRAW ZONE IN PROGRESS =====
    zone_drawer.draw(frame)

    # ===== DRAW DETECTIONS =====
    for det in detections:
        x = int(det.bbox.x)
        y = int(det.bbox.y)
        w = int(det.bbox.w)
        h = int(det.bbox.h)

        label = f"{det.label} {det.confidence:.2f}"

        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(
            frame,
            label,
            (x, max(y - 5, 0)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            2,
        )

        # ===== ZONE CHECK =====
        hits = zone_engine.check(det)
        if hits:
            print("ZONE HIT:", hits)

    cv2.imshow("Video Analytics", frame)

    key = cv2.waitKey(1) & 0xFF

    # ===== SAVE ZONE =====
    if key == 13 and len(zone_drawer.points) >= 3:
        new_zone = Zone(
            id=len(zones) + 1,
            name=f"Zone {len(zones) + 1}",
            polygon=zone_drawer.points.copy(),
            forbidden_classes=["person"],
        )

        zones.append(new_zone)
        zone_engine.zones = zones
        save_zones(zones)

        print(f"Zone {new_zone.id} saved to {ZONES_FILE}")

        zone_drawer.points.clear()

    # ===== EXIT =====
    if key in (27, ord("q")):
        break


# ================== CLEANUP ==================
video.cap.release()
cv2.destroyAllWindows()
