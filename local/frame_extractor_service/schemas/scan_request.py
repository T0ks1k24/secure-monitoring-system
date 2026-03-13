from typing import Optional

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    """
    Network scan settings to search for RTSP cameras.

    The scanner checks the TCP port and tries to connect to the RTSP stream.
    """

    subnet: str = Field(
        description="Підмережа у форматі CIDR. `/24` = 254 хости (~10–30 сек).",
        examples=["192.168.1.0/24", "10.0.0.0/24"],
    )
    ports: list[int] = Field(
        default=[554, 8554],
        description="Порти. 554=стандарт RTSP, 8554=MediaMTX/ffmpeg.",
    )
    credentials: list[dict] = Field(
        default=[
            {"user": "admin", "password": ""},
            {"user": "admin", "password": "admin"},
            {"user": "admin", "password": "12345"},
        ],
        description="Логін/пароль для перевірки підключення.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "🔍 Швидке (тільки порт 554)",
                    "value": {"subnet": "192.168.1.0/24", "ports": [554], "credentials": []},
                },
                {
                    "summary": "🔍 Повне з авторизацією",
                    "value": {
                        "subnet": "192.168.1.0/24", "ports": [554, 8554],
                        "credentials": [
                            {"user": "admin", "password": ""},
                            {"user": "admin", "password": "admin"},
                            {"user": "admin", "password": "12345"},
                        ],
                    },
                },
            ]
        }
    }
