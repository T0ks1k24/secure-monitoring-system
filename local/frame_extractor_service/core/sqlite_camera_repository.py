import logging
from typing import List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from schemas import CameraConfig, MotionConfig
from core.interfaces.i_camera_repository import ICameraRepository
from core.database import Base, CameraModel

logger = logging.getLogger(__name__)

class SQLiteCameraRepository(ICameraRepository):
    """Repository for persisting camera configurations to SQLite."""

    def __init__(self, db_url: str):
        # check_same_thread=False is required for SQLite when accessed from
        # multiple threads (FastAPI thread pool + async event loop workers).
        connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
        self.engine = create_engine(db_url, connect_args=connect_args)
        Base.metadata.create_all(self.engine)
        self.session_local = sessionmaker(bind=self.engine)

    def load_all(self) -> List[CameraConfig]:
        with self.session_local() as session:
            models = session.query(CameraModel).all()
            return [self._to_schema(m) for m in models]

    def save_all(self, cameras: List[CameraConfig]) -> None:
        """Slow bulk update: clears and re-inserts everything."""
        with self.session_local() as session:
            session.query(CameraModel).delete()
            for cam in cameras:
                session.add(self._to_model(cam))
            session.commit()

    def add(self, camera: CameraConfig) -> int:
        with self.session_local() as session:
            model = self._to_model(camera)
            session.add(model)
            session.commit()
            session.refresh(model)
            return model.id

    def update(self, camera: CameraConfig) -> None:
        with self.session_local() as session:
            model = session.query(CameraModel).filter(CameraModel.id == camera.id).first()
            if model:
                model.rtsp = camera.rtsp
                model.name = camera.name
                model.enabled = camera.enabled
                model.fps = camera.fps
                model.resize_width = camera.resize_width
                model.jpeg_quality = camera.jpeg_quality
                model.motion_json = camera.motion.model_dump_json()
                session.commit()

    def delete(self, camera_id: int) -> None:
        with self.session_local() as session:
            session.query(CameraModel).filter(CameraModel.id == camera_id).delete()
            session.commit()

    def _to_schema(self, model: CameraModel) -> CameraConfig:
        data = model.to_dict()
        # Ensure motion is correctly parsed into MotionConfig
        if "motion" in data and isinstance(data["motion"], dict):
            data["motion"] = MotionConfig(**data["motion"])
        return CameraConfig(**data)

    def _to_model(self, schema: CameraConfig) -> CameraModel:
        model = CameraModel(
            rtsp=schema.rtsp,
            name=schema.name,
            enabled=schema.enabled,
            fps=schema.fps,
            resize_width=schema.resize_width,
            jpeg_quality=schema.jpeg_quality,
            motion_json=schema.motion.model_dump_json()
        )
        if schema.id is not None:
            model.id = schema.id
        return model
