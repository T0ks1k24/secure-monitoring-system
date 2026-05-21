import uuid
from domain.repositories.user_repo import UserRepository
from domain.entities.user import User
from domain.enums.role_enum import UserRole
from infrastructure.database import SessionLocal
from infrastructure.models.user_model import UserModel


class UserRepositoryImpl(UserRepository):

    def save(self, user: User) -> User:
        db = SessionLocal()
        try:
            model = UserModel(
                id=user.id,
                username=user.username,
                password_hash=user.password_hash,
                role=user.role.value,
                created_at=user.created_at,
            )
            db.merge(model)
            db.commit()
        finally:
            db.close()
        return user

    def get_all(self) -> list[User]:
        db = SessionLocal()
        try:
            models = db.query(UserModel).all()
        finally:
            db.close()
        return [
            User(
                id=model.id,
                username=model.username,
                password_hash=model.password_hash,
                role=UserRole(model.role),
                created_at=model.created_at,
            )
            for model in models
        ]

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        db = SessionLocal()
        try:
            model = db.query(UserModel).filter(UserModel.id == user_id).first()
        finally:
            db.close()
        if not model:
            return None
        return User(
            id=model.id,
            username=model.username,
            password_hash=model.password_hash,
            role=UserRole(model.role),
            created_at=model.created_at,
        )

    def get_by_username(self, username: str) -> User | None:
        db = SessionLocal()
        try:
            model = db.query(UserModel).filter(UserModel.username == username).first()
        finally:
            db.close()
        if not model:
            return None
        return User(
            id=model.id,
            username=model.username,
            password_hash=model.password_hash,
            role=UserRole(model.role),
            created_at=model.created_at,
        )

    def delete(self, user_id: uuid.UUID) -> None:
        db = SessionLocal()
        try:
            db.query(UserModel).filter(UserModel.id == user_id).delete()
            db.commit()
        finally:
            db.close()
