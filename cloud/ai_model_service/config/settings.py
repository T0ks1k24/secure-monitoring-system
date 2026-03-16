from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Server ────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 5000

    # ── YOLO ──────────────────────────────────────────────────────
    MODEL_PATH: str = "yolov8n.pt"
    # Confidence threshold (0.0–1.0). Нижче = більше детекцій, більше хибних.
    DETECTION_CONFIDENCE: float = 0.4
    # IoU threshold для NMS (прибирає дублікати)
    DETECTION_IOU: float = 0.45
    # Максимум детекцій за кадр
    MAX_DETECTIONS: int = 50
    # Input розмір YOLO. 320=швидко/грубо, 640=баланс, 1280=повільно/точно
    INFERENCE_IMG_SIZE: int = 640
    # Пристрій: "cpu", "cuda", "mps"
    DEVICE: str = "cpu"

    # ── Tracker ───────────────────────────────────────────────────
    # Секунди зберігати трек після зникнення об'єкта
    TRACKER_MAX_AGE_SECONDS: float = 3.0
    # Мінімум підтверджень щоб трек став «активним» (фільтр хибних)
    TRACKER_MIN_HITS: int = 2
    # IoU для матчингу нових детекцій з існуючими треками
    TRACKER_IOU_THRESHOLD: float = 0.3

    # ── Zone cache ────────────────────────────────────────────────
    # Після цього TTL — перезавантажуємо зони з Backend API
    ZONE_CACHE_TTL: float = 30.0
    # URL Backend для GET /api/zones?camera_id=X
    BACKEND_API_URL: str = "http://localhost:8000"

    # ── RabbitMQ ──────────────────────────────────────────────────
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    # Topic exchange — публікуємо події (person_detected, weapon_detected…)
    EVENTS_EXCHANGE: str = "security.events"
    # Topic exchange — слухаємо zone-updates від Backend
    ZONES_EXCHANGE: str = "security.zones"

    # ── Risk / Trajectory ─────────────────────────────────────────
    # Скільки кадрів зберігати для аналізу траєкторії
    TRAJECTORY_HISTORY_FRAMES: int = 30
    # Мінімальна швидкість (px/frame) що вважається «рухом»
    TRAJECTORY_MIN_SPEED_PX: float = 5.0
    
    # ── Frame saving ──────────────────────────────────────────────
    # Включає/виключає збереження оброблених кадрів з оверлеями
    SAVE_PROCESSED_FRAMES: bool = False
    # Шлях до папки зі збереженими кадрами
    FRAME_STORAGE_PATH: str = "storage/frames"

    # ── Debug ─────────────────────────────────────────────────────
    # Включає/виключає відображення кадрів з результатами (cv2.imshow)
    DEBUG_VISUALIZE: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}

    def update(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if v is not None and hasattr(self, k):
                object.__setattr__(self, k, v)


settings = Settings()
