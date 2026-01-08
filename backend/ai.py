from ultralytics import YOLO

model = YOLO("yolov8n.pt")


def analyze_video_stream():
    results = model("test.mp4", conf=0.5, stream=True)

    for r in results:
        person_detected = False
        max_conf = 0.0

        for box in r.boxes:
            if int(box.cls[0]) == 0:  # person
                person_detected = True
                max_conf = max(max_conf, float(box.conf[0]))

        if person_detected:
            yield {"event": "person_detected", "confidence": max_conf}
