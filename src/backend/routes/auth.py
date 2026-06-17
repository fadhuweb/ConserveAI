import secrets

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.backend.auth.dependencies import require_admin, get_current_user
from src.backend.auth.jwt_handler import create_access_token, create_reset_token, decode_reset_token
from src.backend.auth.password import hash_password, verify_password, password_problems
from src.backend.config import settings
from src.backend.database import get_db
from src.backend.models.user import User, Role
from src.backend.schemas.auth import (
    LoginRequest, TokenResponse, CreateUserRequest, UserOut, ChangePasswordRequest,
    ForgotPasswordRequest, ResetPasswordRequest, SetActiveRequest,
)
from src.backend.services.email import send_temporary_password, send_reset_link

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, summary="Log in — sets JWT httpOnly cookie")
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="This account has been deactivated. Contact your administrator.")

    token = create_access_token({"sub": user.username, "role": user.role, "park_id": user.park_id})

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=28800,   # 8 hours
    )
    return TokenResponse(
        username=user.username,
        role=user.role,
        park_id=user.park_id,
        must_change_password=user.must_change_password,
        message=("Password change required" if user.must_change_password else "Login successful"),
    )


@router.post("/logout", summary="Log out — clears the auth cookie")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserOut, summary="Current account's own profile")
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[UserOut], summary="List all accounts (admin only)")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.query(User).order_by(User.role.desc(), User.username).all()


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user account (admin only)",
)
def create_user(
    body: CreateUserRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Provision a new account. Admin-only — there is no public self-registration.

    Managers must be bound to a valid park; admins are not park-scoped.
    """
    role = body.role.lower()
    if role not in ("manager", "admin"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="role must be 'manager' or 'admin'")

    park_id = body.park_id
    if role == "manager":
        if not park_id or park_id not in settings.parks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"a manager requires a valid park_id, one of: {settings.parks}",
            )
        if not body.email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="a manager requires an email address — the temporary password is sent there",
            )
    else:
        park_id = None   # admins span all parks

    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="username already exists")

    # The system generates the temporary password; the admin never sees it.
    temp_password = secrets.token_urlsafe(9)

    user = User(
        username=body.username,
        full_name=body.full_name,
        password_hash=hash_password(temp_password),
        role=Role(role),
        park_id=park_id,
        email=body.email,
        phone=body.phone,
        must_change_password=True,   # manager must set their own password on first login
    )
    db.add(user)
    db.flush()   # validate before sending; keeps transaction open

    # Email the temporary password to the new user. If delivery fails, roll back
    # so we never create an account whose password nobody can retrieve.
    if body.email:
        try:
            send_temporary_password(body.email, body.username, body.full_name, temp_password)
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Account not created — could not email the temporary password: {exc}",
            )

    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password", summary="Change your password (clears the forced-change flag)")
def change_password(
    body: ChangePasswordRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Authenticated password change. Required on first login for admin-provisioned
    accounts; afterwards the long-term password is known only to the account holder."""
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Current password is incorrect")
    problems = password_problems(body.new_password)
    if problems:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Password must contain " + ", ".join(problems))

    current_user.password_hash = hash_password(body.new_password)
    current_user.must_change_password = False
    db.commit()

    # Invalidate the current session so the next login uses the new password.
    response.delete_cookie("access_token")
    return {"message": "Password changed. Please log in again."}


@router.post("/forgot-password", summary="Self-service reset — emails a secure reset link")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Email a time-limited reset link to the account on file.

    Always returns the same generic message so the endpoint can't be used to probe
    which usernames exist. The password is NOT changed here — the user sets it
    themselves via the link (/auth/reset-password).
    """
    generic = {"message": "If that account exists, a reset link has been emailed to it."}

    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not user.email:
        return generic

    token = create_reset_token(user.username)
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"
    try:
        send_reset_link(user.email, user.username, user.full_name, reset_url)
    except Exception:
        return generic

    return generic


@router.post("/reset-password", summary="Set a new password using a reset-link token")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Validate the reset token and set the new password directly."""
    username = decode_reset_token(body.token)
    if username is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="This reset link is invalid or has expired. Request a new one.")
    problems = password_problems(body.new_password)
    if problems:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Password must contain " + ", ".join(problems))

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="This reset link is invalid or has expired. Request a new one.")

    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False   # they just set it themselves
    db.commit()
    return {"message": "Password updated. You can now log in with your new password."}


# ── Admin account actions ───────────────────────────────────────────────────────

@router.post("/users/{user_id}/reset-password", summary="Email a reset link to an account (admin only)")
def admin_reset_password(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Admin-triggered reset. Emails the account holder a secure link so they set
    their own new password — the admin never sees or sets it."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if not user.email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="This account has no email on file, so a reset link can't be sent")

    token = create_reset_token(user.username)
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"
    try:
        send_reset_link(user.email, user.username, user.full_name, reset_url)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Could not send the reset email: {exc}")
    return {"message": f"Reset link emailed to {user.email}."}


@router.post("/users/{user_id}/active", summary="Activate or deactivate an account (admin only)")
def set_user_active(
    user_id: int,
    body: SetActiveRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Block or restore sign-in for an account without deleting it. Admins cannot
    deactivate their own account (prevents locking yourself out)."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if user.id == admin.id and not body.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="You can't deactivate your own account")

    user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    return {"message": f"Account {'activated' if body.is_active else 'deactivated'}.",
            "is_active": user.is_active}