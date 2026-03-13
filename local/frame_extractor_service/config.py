from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8100

    # AI service
    AI_SERVICE_URL: str = "http://localhost:5000/api/v1/detect"
    AI_REQUEST_TIMEOUT: int = 5

    # Default for new cameras
    DEFAULT_FPS: float = 2.0
    DEFAULT_RESIZE_WIDTH: int = 1280
    DEFAULT_JPEG_QUALITY: int = 95
    DEFAULT_RECONNECT_DELAY: int = 3

    # Scan
    SCANNER_TIMEOUT: float = 1.0
    SCANNER_MAX_WORKERS: int = 64

    # Save config
    CAMERAS_CONFIG_PATH: str = "cameras.json"

    model_config = {"env_file": ".env", "extra": "ignore"}

    def update(self, **kwargs) -> None:
        for key, val in kwargs.items():
            if val is not None and hasattr(self, key):
                object.__setattr__(self, key, val)


settings = Settings()
