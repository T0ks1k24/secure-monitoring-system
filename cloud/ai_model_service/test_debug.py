import asyncio
import cv2
import numpy as np
import time
from schemas.events import DetectRequest
from services.pipeline import AnalyzePipeline
from models.detector import detector
from config.settings import settings

async def run():
    print("--- DEBUG START ---")
    
    print("Setting config...")
    settings.DEBUG_VISUALIZE = True
    
    print("Loading model...")
    detector.load()
    
    pipeline = AnalyzePipeline()
    
    print("Creating test image...")
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(img, "DEBUG VISUALIZATION", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    
    req = DetectRequest(camera_id="cam_debug")
    
    print("Starting pipeline process (imshow should trigger)...")
    try:
        # process calls debug_visualizer.show
        await pipeline.process(img, req)
        print("Pipeline process called show().")
    except Exception as e:
        print(f"Error during process: {e}")
        return

    print("Entering wait cycle (window should be visible)...")
    for i in range(5):
        print(f"Waiting... {5-i}")
        cv2.waitKey(1000)
    
    print("Closing windows...")
    cv2.destroyAllWindows()
    print("--- DEBUG END ---")

if __name__ == "__main__":
    asyncio.run(run())
