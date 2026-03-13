from typing import Optional, Protocol, Tuple
import numpy as np

class IFrameSource(Protocol):
    """Protocol for reading frames from a source (e.g. RTSP camera)."""
    
    async def connect(self) -> bool:
        """Establish connection to the source."""
        ...
        
    async def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read a single frame. Returns (success, frame)."""
        ...
        
    async def release(self) -> None:
        """Release the connection and free resources."""
        ...
