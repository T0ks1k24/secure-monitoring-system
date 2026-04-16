from domain.repositories.user_repo import UserRepository
from domain.entities.user import User
from domain.enums.role_enum import UserRole
from core.security import hash_password, verify_password, create_access_token, create_refresh_token
import uuid


class AuthService:

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def login(self, username: str, password: str):

        user = self.user_repo.get_by_username(username)

        if not user:
            raise Exception("User not found")

        if not verify_password(password, user.password_hash):
            raise Exception("Invalid credentials")

        access = create_access_token(user_id=str(user.id), role=user.role.value)

        refresh = create_refresh_token(user_id=str(user.id))

        return access, refresh

    def create_user(self, username: str, password: str, role: UserRole):

        user = User(username=username, password_hash=hash_password(password), role=role)

        self.user_repo.save(user)
        return user

    def get_all_users(self):
        users = self.user_repo.get_all()
        return users

    def get_user_by_id(self, user_id: uuid.UUID):
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise Exception("User not found")
        return user

    def reset_password(self, user_id: uuid.UUID, new_password: str):

        user = self.user_repo.get_by_id(user_id)

        if not user:
            raise Exception("User not found")

        user.password_hash = hash_password(new_password)

        self.user_repo.save(user)

        return user
