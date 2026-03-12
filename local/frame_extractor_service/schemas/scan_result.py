from pydantic import BaseModel, Field
from .discovered_camera import DiscoveredCamera

class ScanResult(BaseModel):
    """Network scan results."""
    subnet: str
    ports_scanned: list[int]
    hosts_scanned: int              = Field(description="Перевірено хостів")
    found: list[DiscoveredCamera]   = Field(description="Знайдені камери")
    scan_duration_sec: float        = Field(description="Тривалість сканування (сек)")
