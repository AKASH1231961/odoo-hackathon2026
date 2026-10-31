import uuid
import enum
from sqlalchemy import Column, String, Numeric, Boolean, Date, Integer, Enum, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.types import GUID


class DiscountType(str, enum.Enum):
    fixed = "fixed"
    percentage = "percentage"


class DiscountScope(str, enum.Enum):
    product = "product"
    subscription = "subscription"


class Discount(Base):
    __tablename__ = "discounts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(Enum(DiscountType), nullable=False)
    value = Column(Numeric(12, 2), nullable=False)
    min_purchase = Column(Numeric(12, 2), nullable=True)
    min_quantity = Column(Integer, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    max_uses = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0, nullable=False)
    scope = Column(Enum(DiscountScope), nullable=False)
    product_id = Column(GUID(), ForeignKey("products.id"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

