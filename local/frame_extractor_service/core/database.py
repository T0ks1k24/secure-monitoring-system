import json
from sqlalchemy import Column, Integer, String, Boolean, Float, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class CameraModel(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True)
    rtsp = Column(String, nullable=False)
    name = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    fps = Column(Float, nullable=True)
    resize_width = Column(Integer, nullable=True)
    jpeg_quality = Column(Integer, nullable=True)

    # Store MotionConfig as JSON string for simplicity in SQLite
    motion_json = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "rtsp": self.rtsp,
            "name": self.name,
            "enabled": self.enabled,
            "fps": self.fps,
            "resize_width": self.resize_width,
            "jpeg_quality": self.jpeg_quality,
            "motion": json.loads(self.motion_json) if self.motion_json else {}
        }
