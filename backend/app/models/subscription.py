import uuid
import enum
from sqlalchemy import (
    Column, String, Date, DateTime, ForeignKey, Enum, Integer, Numeric, CheckConstraint, Index,
)
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
    __table_args__ = (
        CheckConstraint("payment_terms >= 0", name="ck_subscriptions_payment_terms"),
        CheckConstraint("expiry_date >= start_date", name="ck_subscriptions_dates"),
        Index("ix_subscriptions_created_at", "created_at"),
        Index("ix_subscriptions_status_next_billing", "status", "next_billing_date"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    subscription_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(GUID(), ForeignKey("plans.id"), nullable=False, index=True)
    variant_id = Column(GUID(), ForeignKey("product_variants.id"), nullable=True, index=True)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.draft, nullable=False, index=True)
    start_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    # Set when the quotation is sent; it cannot be confirmed after this date
    quotation_valid_until = Column(Date, nullable=True)
    # next_billing_date: drives the Celery billing cycle task (not in spec tables, necessary for automation)
    next_billing_date = Column(Date, nullable=True, index=True)
    payment_terms = Column(Integer, default=15, server_default="15", nullable=False)
    template_id = Column(GUID(), ForeignKey("quotation_templates.id"), nullable=True, index=True)
    created_by = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    plan = relationship("Plan")
    variant = relationship("ProductVariant")
    customer = relationship("User", foreign_keys=[customer_id])
    creator = relationship("User", foreign_keys=[created_by])
    template = relationship("QuotationTemplate")
    lines = relationship("SubscriptionLine", back_populates="subscription", cascade="all, delete-orphan")
    status_history = relationship(
        "SubscriptionStatusHistory",
        back_populates="subscription",
        cascade="all, delete-orphan",
        order_by="SubscriptionStatusHistory.changed_at",
    )

    @property
    def customer_name(self):
        return self.customer.full_name if self.customer else None

    @property
    def plan_name(self):
        return self.plan.name if self.plan else None


class SubscriptionLine(Base):
    __tablename__ = "subscription_lines"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_subscription_lines_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_subscription_lines_unit_price"),
        CheckConstraint("tax_amount >= 0", name="ck_subscription_lines_tax"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(GUID(), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(GUID(), ForeignKey("products.id"), nullable=False, index=True)
    variant_id = Column(GUID(), ForeignKey("product_variants.id"), nullable=True, index=True)
    quantity = Column(Integer, default=1, server_default="1", nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), default=0, server_default="0", nullable=False)
    line_total = Column(Numeric(12, 2), nullable=False)

    subscription = relationship("Subscription", back_populates="lines")
    product = relationship("Product")
    variant = relationship("ProductVariant")


class SubscriptionStatusHistory(Base):
    __tablename__ = "subscription_status_history"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(
        GUID(),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status = Column(Enum(SubscriptionStatus), nullable=True)
    to_status = Column(Enum(SubscriptionStatus), nullable=False)
    changed_by = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    subscription = relationship("Subscription", back_populates="status_history")
    actor = relationship("User")
