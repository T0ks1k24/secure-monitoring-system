import threading
from ultralytics import YOLO
from app.streaming.frame_queue import get_camera_queue

model = YOLO("yolov8n.pt")


def camera_worker(camera_id):

    queue = get_camera_queue(camera_id)

    while True:

        frame = queue.get()

        results = model(frame)

        persons = 0

        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])

                if cls == 0:
                    persons += 1

        print(f"{camera_id} → persons: {persons}")


def start_camera_worker(camera_id):

    t = threading.Thread(
        target=camera_worker,
        args=(camera_id,),
        daemon=True
    )

    t.start()
