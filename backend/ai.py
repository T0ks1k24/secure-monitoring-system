from ultralytics import YOLO

model = YOLO("yolov8n.pt")


def analyze_video():
    results = model("test.mp4", conf=0.5)
    events = []

    for r in results:
        for box in r.boxes:
            if int(box.cls[0]) == 0:  # person
                events.append(
                    {"event": "person_detected", "confidence": float(box.conf[0])}
                )

    return events
