import uuid
import enum
from sqlalchemy import Column, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.types import GUID


class UserRole(str, enum.Enum):
    admin = "admin"
    staff = "staff"
    customer = "customer"


class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.customer)
    is_active = Column(Boolean, default=True, nullable=False)
    reset_token = Column(String(128), nullable=True)
    reset_token_expiry = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

