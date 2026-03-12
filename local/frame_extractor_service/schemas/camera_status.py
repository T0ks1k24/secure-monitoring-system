from enum import Enum

class CameraStatus(str, Enum):
    RUNNING    = "running"
    STOPPED    = "stopped"
    CONNECTING = "connecting"
    ERROR      = "error"
