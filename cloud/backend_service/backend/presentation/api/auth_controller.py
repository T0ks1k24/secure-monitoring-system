import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from application.services.auth_service import AuthService
from infrastructure.repositories.user_repo_impl import UserRepositoryImpl
from domain.enums.role_enum import UserRole
from core.jwt_auth import admin_required
from jose import jwt
from core.config import settings
from core.security import create_access_token


router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    username: str = Field(..., description="Логін користувача для входу.")
    password: str = Field(..., description="Пароль користувача.")


class CreateUserRequest(BaseModel):
    username: str = Field(..., description="Логін нового користувача.")
    password: str = Field(..., description="Початковий пароль нового користувача.")
    role: UserRole = Field(..., description="Роль користувача (admin/operator).")


class ResetPasswordRequest(BaseModel):
    user_id: str = Field(..., description="ID користувача, якому потрібно скинути пароль.")
    new_password: str = Field(..., description="Новий пароль користувача.")


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    role: UserRole
    created_at: str

    class Config:
        from_attributes = True


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh JWT токен для отримання нового access token.")


def get_auth_service():

    return AuthService(
        user_repo=UserRepositoryImpl()
    )


# LOGIN
@router.post("/login")
def login(
    data: LoginRequest,
    service: AuthService = Depends(get_auth_service)
):

    try:
        access, refresh = service.login(
            data.username,
            data.password
        )

        return {
            "access_token": access,
            "refresh_token": refresh
        }

    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


# GET ALL USERS (ADMIN)
@router.get("/users", response_model=list[UserResponse])
def get_all_users(
    admin=Depends(admin_required),
    service: AuthService = Depends(get_auth_service)
):
    users = service.get_all_users()
    return [
        UserResponse(
            id=u.id,
            username=u.username,
            role=u.role,
            created_at=u.created_at.isoformat()
        ) for u in users
    ]


# GET USER BY ID (ADMIN)
@router.get("/users/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: uuid.UUID,
    admin=Depends(admin_required),
    service: AuthService = Depends(get_auth_service)
):
    try:
        user = service.get_user_by_id(user_id)
        return UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            created_at=user.created_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# CREATE USER (ADMIN)
@router.post("/users")
def create_user(
    data: CreateUserRequest,
    admin=Depends(admin_required),
    service: AuthService = Depends(get_auth_service)
):

    user = service.create_user(
        username=data.username,
        password=data.password,
        role=data.role
    )

    return {
        "id": str(user.id),
        "username": user.username,
        "role": user.role.value
    }


# RESET PASSWORD (ADMIN)
@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    admin=Depends(admin_required),
    service: AuthService = Depends(get_auth_service)
):

    user = service.reset_password(
        user_id=uuid.UUID(str(data.user_id)),
        new_password=data.new_password
    )

    return {"status": "password_updated"}



@router.post("/refresh")
def refresh(
    data: RefreshRequest,
    service: AuthService = Depends(get_auth_service)
):

    try:
        payload = jwt.decode(
            data.refresh_token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Wrong token type")

        user = service.user_repo.get_by_id(payload["sub"])
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        new_access = create_access_token(
            user_id=str(user.id),
            role=user.role.value
        )

        return {"access_token": new_access}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
