from typing import Protocol
import numpy as np

class IFrameSink(Protocol):
    """Protocol for sending or storing a processed frame."""

    async def send(self, frame: np.ndarray, source_id: str, quality: int) -> bool:
        """Send the frame to the destination. Returns True on success."""

    async def close(self) -> None:
        """Close connection to the sink if needed."""
