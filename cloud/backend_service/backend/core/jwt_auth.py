from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from core.config import settings
from domain.enums.role_enum import UserRole
from datetime import datetime, timedelta


security = HTTPBearer()


def decode_token(token: str):

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    payload = decode_token(credentials.credentials)

    return payload


def admin_required(
    user=Depends(get_current_user)
):

    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")

    return user


def create_refresh_token(data: dict):

    expire = datetime.utcnow() + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    data.update({"exp": expire})

    return jwt.encode(
        data,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
