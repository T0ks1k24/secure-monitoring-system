from fastapi import FastAPI, UploadFile, File, Form
import cv2
import numpy as np
from ultralytics import YOLO
import uvicorn

app = FastAPI(title="Security AI Model Service")

# Завантажуємо модель YOLOv8s (small) при старті сервера.
# Вона автоматично завантажиться з інтернету при першому запуску.
print("Loading YOLOv8 model...")
model = YOLO("yolov8s.pt")
print("Model loaded successfully!")

@app.post("/detect")
async def detect_objects(
    camera_id: str = Form(...),
    image: UploadFile = File(...)
):
    # 1. Читаємо байти отриманого зображення
    image_bytes = await image.read()

    # 2. Конвертуємо байти в масив NumPy, а потім у формат OpenCV
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        return {"error": "Invalid image format"}

    # 3. Запускаємо детекцію (conf=0.5 означає, що беремо лише впевнені результати >= 50%)
    results = model(frame, conf=0.5, verbose=False)

    detections = []

    # 4. Розбираємо результати від YOLO
    for r in results:
        boxes = r.boxes
        for box in boxes:
            # Витягуємо координати рамки [x1, y1, x2, y2]
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            # Впевненість
            conf = float(box.conf[0])
            # Клас об'єкта (наприклад, 0 - людина, 2 - авто)
            cls_id = int(box.cls[0])
            cls_name = model.names[cls_id]

            detections.append({
                "class": cls_name,
                "confidence": round(conf, 2),
                "bbox": [round(x1), round(y1), round(x2), round(y2)]
            })

    # Виводимо лог у термінал для зручності відлагодження
    detected_classes = [d['class'] for d in detections]
    print(f"[{camera_id}] Found {len(detections)} objects: {detected_classes}")

    # Повертаємо JSON відповідь
    return {
        "camera_id": camera_id,
        "detections": detections
    }

if __name__ == "__main__":
    # Запускаємо сервер на 5000 порту (як вказано у конфігу твого екстрактора)
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
