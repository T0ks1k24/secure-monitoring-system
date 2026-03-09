from ultralytics import YOLO
import os


MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "yolov8n.pt"
)

model = YOLO(MODEL_PATH)
model.fuse()

print("[AI] YOLO model loaded successfully")
