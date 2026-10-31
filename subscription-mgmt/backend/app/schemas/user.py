import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        from app.core.security import validate_password_policy
        if not validate_password_policy(v):
            raise ValueError(
                "Password must be at least 8 characters with at least one uppercase letter, "
                "one lowercase letter, and one special character"
            )
        return v


class StaffCreate(UserCreate):
    role: UserRole = UserRole.staff


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None

