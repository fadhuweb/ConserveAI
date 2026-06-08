from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.backend.auth.jwt_handler import create_access_token
from src.backend.auth.password import verify_password
from src.backend.database import get_db
from src.backend.models.user import User
from src.backend.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, summary="Log in — sets JWT httpOnly cookie")
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"sub": user.username, "role": user.role, "park_id": user.park_id})

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=28800,   # 8 hours
    )
    return TokenResponse(username=user.username, role=user.role, park_id=user.park_id)


@router.post("/logout", summary="Log out — clears the auth cookie")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out"}