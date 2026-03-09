import cv2
import time
# Додаємо імпорт сюди
from ai_client import AIClient

def camera_worker(camera, config, ai_endpoint):
    # Ініціалізуємо клієнт всередині ізольованого процесу
    ai_client = AIClient(ai_endpoint)

    camera_id = camera["id"]
    rtsp = camera["rtsp"]

    fps = config["target_fps"]
    resize_width = config["resize_width"]
    reconnect_delay = config["reconnect_delay"]

    frame_interval = 1 / fps

    cap = None
    last_time = 0

    print(f"[{camera_id}] worker started")

    while True:
        if cap is None or not cap.isOpened():
            print(f"[{camera_id}] connecting {rtsp}")
            cap = cv2.VideoCapture(rtsp, cv2.CAP_FFMPEG)

            if not cap.isOpened():
                print(f"[{camera_id}] connection failed")
                time.sleep(reconnect_delay)
                continue

            print(f"[{camera_id}] connected")

        ret, frame = cap.read()

        if not ret:
            print(f"[{camera_id}] frame lost")
            cap.release()
            cap = None
            time.sleep(reconnect_delay)
            continue

        now = time.time()

        if now - last_time < frame_interval:
            continue

        last_time = now

        if resize_width > 0:
            h, w = frame.shape[:2]
            ratio = resize_width / w
            new_h = int(h * ratio)
            frame = cv2.resize(frame, (resize_width, new_h))

        ai_client.send_frame(frame, camera_id)
