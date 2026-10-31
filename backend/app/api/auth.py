import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core import rate_limit
from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token, validate_password_policy,
    hash_reset_token, is_future,
)
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate, UserOut, TokenPair, RefreshRequest,
    ForgotPasswordRequest, ResetPasswordRequest, UserLogin,
)
from app.utils.email import send_email
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])


def _authenticate(email: str, password: str, request: Request, db: Session) -> TokenPair:
    email = email.strip().lower()
    client = request.client.host if request.client else "unknown"
    key = f"{email}:{client}"
    if rate_limit.is_locked(key):
        raise HTTPException(429, "Too many failed attempts. Try again later.")
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        rate_limit.record_failure(key)
        raise HTTPException(401, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(403, "Account is disabled")
    rate_limit.clear(key)
    return TokenPair(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """Self-registration for customers."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=UserRole.customer,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Return access + refresh token pair on valid credentials."""
    return _authenticate(payload.email, payload.password, request, db)


@router.post("/login/form", response_model=TokenPair, include_in_schema=False)
def login_form(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2 password form login — used by Swagger UI."""
    return _authenticate(form.username, form.password, request, db)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Issue a new access token using a valid refresh token."""
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")
    except Exception:
        raise HTTPException(401, "Invalid or expired refresh token")

    user = db.query(User).filter(User.id == data["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")

    return TokenPair(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send a password reset link. Always returns 200 to avoid user enumeration."""
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token = hash_reset_token(token)
        user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        db.add(user)
        db.commit()
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        send_email(
            user.email,
            "Brightloop — Password Reset Request",
            f"Click the link below to reset your password (expires in 1 hour):\n\n{reset_link}\n\n"
            "If you did not request this, ignore this email.",
        )
    return {"message": "If that email is registered, a reset link has been sent"}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Validate reset token and set new password."""
    user = db.query(User).filter(User.reset_token == hash_reset_token(payload.token)).first()
    if not user or not user.reset_token_expiry or not is_future(user.reset_token_expiry):
        raise HTTPException(400, "Invalid or expired reset token")
    if not validate_password_policy(payload.new_password):
        raise HTTPException(
            400,
            "Password must be more than 8 characters with uppercase, lowercase, and a special character",
        )
    user.password_hash = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.add(user)
    db.commit()
    return {"message": "Password reset successfully"}

