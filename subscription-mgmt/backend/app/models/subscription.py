import uuid
import enum
from sqlalchemy import Column, String, Date, DateTime, ForeignKey, Enum, Integer, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.types import GUID


class SubscriptionStatus(str, enum.Enum):
    draft = "draft"
    quotation = "quotation"
    confirmed = "confirmed"
    active = "active"
    paused = "paused"
    closed = "closed"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    subscription_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(GUID(), ForeignKey("plans.id"), nullable=False, index=True)
    variant_id = Column(GUID(), ForeignKey("product_variants.id"), nullable=True)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.draft, nullable=False, index=True)
    start_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    # next_billing_date: drives the Celery billing cycle task (not in spec tables, necessary for automation)
    next_billing_date = Column(Date, nullable=True, index=True)
    payment_terms = Column(Integer, default=15, nullable=False)
    template_id = Column(GUID(), ForeignKey("quotation_templates.id"), nullable=True)
    created_by = Column(GUID(), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    plan = relationship("Plan")
    customer = relationship("User", foreign_keys=[customer_id])
    creator = relationship("User", foreign_keys=[created_by])
    lines = relationship("SubscriptionLine", back_populates="subscription", cascade="all, delete-orphan")


class SubscriptionLine(Base):
    __tablename__ = "subscription_lines"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(GUID(), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(GUID(), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), default=0, nullable=False)
    line_total = Column(Numeric(12, 2), nullable=False)

    subscription = relationship("Subscription", back_populates="lines")
    product = relationship("Product")

