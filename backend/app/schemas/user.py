import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        from app.core.security import validate_password_policy
        if not validate_password_policy(v):
            raise ValueError(
                "Password must be more than 8 characters with at least one uppercase letter, "
                "one lowercase letter, and one special character"
            )
        return v


class StaffCreate(UserCreate):
    role: UserRole = UserRole.staff

    @field_validator("role")
    @classmethod
    def internal_roles_only(cls, v: UserRole) -> UserRole:
        if v == UserRole.customer:
            raise ValueError("Customers register themselves")
        return v


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    # Deliberately not EmailStr: format rules belong to sign-up, not to signing in
    email: str
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    password: Optional[str] = None

