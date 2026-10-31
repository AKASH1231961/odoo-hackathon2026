import re
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    # bcrypt limits passwords to 72 bytes
    if isinstance(password, str):
        password = password[:72]
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if isinstance(plain, str):
        plain = plain[:72]
    return pwd_context.verify(plain, hashed)


def validate_password_policy(password: str) -> bool:
    """Enforce: 8+ chars, uppercase, lowercase, special character."""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[\W_]", password):
        return False
    return True


def _create_token(data: dict, expires_delta: timedelta, token_type: str) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire, "type": token_type})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, role: str) -> str:
    return _create_token(
        {"sub": user_id, "role": role},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "access",
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        {"sub": user_id},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "refresh",
    )


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

