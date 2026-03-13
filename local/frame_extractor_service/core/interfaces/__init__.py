from .i_frame_source import IFrameSource
from .i_frame_processor import IFrameProcessor
from .i_frame_sink import IFrameSink
from .i_ai_client import IAIClient
from .i_camera_repository import ICameraRepository
from .i_camera_worker_factory import ICameraWorkerFactory

__all__ = [
    "IFrameSource",
    "IFrameProcessor",
    "IFrameSink",
    "IAIClient",
    "ICameraRepository",
    "ICameraWorkerFactory",
]
