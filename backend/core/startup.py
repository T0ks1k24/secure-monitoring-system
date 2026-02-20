from infrastructure.repositories.user_repo_impl import UserRepositoryImpl
from domain.entities.user import User
from domain.enums.role_enum import UserRole
from core.security import hash_password


def create_default_admin():

    repo = UserRepositoryImpl()

    admin = repo.get_by_username("admin")

    if not admin:

        user = User(
            username="admin",
            password_hash=hash_password("admin"),
            role=UserRole.ADMIN
        )

        repo.save(user)

        print("✅ Default admin created")
