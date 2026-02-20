from ultralytics import YOLO

model = None

def load_model():
    global model
    if model is None:
        model = YOLO("yolov8n.pt")
    return model
