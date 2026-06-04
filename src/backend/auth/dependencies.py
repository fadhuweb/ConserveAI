"""FastAPI dependencies for authentication and park-scoping."""

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.backend.auth.jwt_handler import decode_token
from src.backend.database import get_db
from src.backend.models.user import User


def _get_user_from_token(token: str, db: Session) -> User:
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.query(User).filter(User.username == payload.get("sub")).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_current_user(
    access_token: str = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return _get_user_from_token(access_token, db)


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def park_scoped(park: str, current_user: User = Depends(get_current_user)) -> User:
    """Allow admins to access any park; managers only their own."""
    if current_user.role == "admin":
        return current_user
    if current_user.park_id != park:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this park")
    return current_user