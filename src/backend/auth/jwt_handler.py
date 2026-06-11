from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from src.backend.config import settings


def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire  = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload["exp"] = expire
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def create_reset_token(username: str, minutes: int = 30) -> str:
    """Short-lived, single-purpose token for the password-reset link."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": username, "purpose": "reset", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_reset_token(token: str) -> Optional[str]:
    """Return the username if the token is a valid, unexpired reset token, else None."""
    data = decode_token(token)
    if not data or data.get("purpose") != "reset":
        return None
    return data.get("sub")