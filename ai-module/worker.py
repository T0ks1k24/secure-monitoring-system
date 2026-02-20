import base64
import cv2
import numpy as np
from queue_manager import frame_queue, result_queue
from detector import load_model


def inference_worker():

    model = load_model()

    while True:

        camera_id, frame_base64 = frame_queue.get()

        jpg_bytes = base64.b64decode(frame_base64)

        np_arr = np.frombuffer(jpg_bytes, np.uint8)

        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        results = model(frame)

        detections = []

        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()

                detections.append({
                    "class": cls,
                    "conf": conf,
                    "bbox": xyxy
                })

        result_queue.put((camera_id, detections))
