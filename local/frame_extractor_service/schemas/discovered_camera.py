from typing import Optional

from pydantic import BaseModel, Field

class DiscoveredCamera(BaseModel):
    """Camera found during scan."""
    ip: str
    port: int
    rtsp_url: str                     = Field(description="Готовий RTSP URL")
    reachable: bool                   = Field(description="TCP порт відповідає")
    connectable: bool                 = Field(description="Вдалось підключитись до RTSP")
    credentials_used: Optional[dict]  = Field(default=None, description="Credentials що спрацювали")
    suggested_id: str                 = Field(description="Запропонований ID для POST /cameras")

