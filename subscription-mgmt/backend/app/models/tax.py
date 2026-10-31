import uuid
import enum
from sqlalchemy import Column, String, Numeric, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.types import GUID


class TaxAppliesTo(str, enum.Enum):
    all = "all"
    product = "product"
    plan = "plan"


class TaxRule(Base):
    __tablename__ = "tax_rules"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    rate = Column(Numeric(5, 4), nullable=False)  # e.g. 0.1800 = 18%
    applies_to = Column(Enum(TaxAppliesTo), default=TaxAppliesTo.all, nullable=False)
    product_id = Column(GUID(), ForeignKey("products.id"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

