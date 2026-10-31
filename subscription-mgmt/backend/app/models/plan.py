import uuid
import enum
from sqlalchemy import Column, String, Numeric, Boolean, Date, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.types import GUID


class BillingInterval(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class Plan(Base):
    __tablename__ = "plans"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    product_id = Column(GUID(), ForeignKey("products.id"), nullable=False, index=True)
    billing_interval = Column(Enum(BillingInterval), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    min_quantity = Column(Integer, default=1, nullable=False)
    available_from = Column(Date, nullable=True)
    available_to = Column(Date, nullable=True)
    auto_close = Column(Boolean, default=False, nullable=False)
    can_pause = Column(Boolean, default=True, nullable=False)
    can_close_early = Column(Boolean, default=True, nullable=False)
    can_renew = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product = relationship("Product")

