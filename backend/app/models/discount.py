import uuid
import enum
from sqlalchemy import (
    Column,
    String,
    Numeric,
    Boolean,
    Date,
    Integer,
    Enum,
    ForeignKey,
    DateTime,
    Table,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.types import GUID


discount_products = Table(
    "discount_products",
    Base.metadata,
    Column("discount_id", GUID(), ForeignKey("discounts.id", ondelete="CASCADE"), primary_key=True),
    Column("product_id", GUID(), ForeignKey("products.id"), primary_key=True, index=True),
)


class DiscountType(str, enum.Enum):
    fixed = "fixed"
    percentage = "percentage"


class DiscountScope(str, enum.Enum):
    product = "product"
    subscription = "subscription"


class Discount(Base):
    __tablename__ = "discounts"
    __table_args__ = (
        CheckConstraint("value > 0", name="ck_discounts_value"),
        CheckConstraint("type <> 'percentage' OR value <= 100", name="ck_discounts_percentage"),
        CheckConstraint("min_purchase >= 0", name="ck_discounts_min_purchase"),
        CheckConstraint("min_quantity >= 1", name="ck_discounts_min_quantity"),
        CheckConstraint("end_date >= start_date", name="ck_discounts_dates"),
        CheckConstraint("max_uses >= 1", name="ck_discounts_max_uses"),
        CheckConstraint("used_count >= 0", name="ck_discounts_used_count"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(Enum(DiscountType), nullable=False)
    value = Column(Numeric(12, 2), nullable=False)
    min_purchase = Column(Numeric(12, 2), nullable=True)
    min_quantity = Column(Integer, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    max_uses = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0, server_default="0", nullable=False)
    scope = Column(Enum(DiscountScope), nullable=False)
    product_id = Column(GUID(), ForeignKey("products.id"), nullable=True, index=True)
    # Optional targeting: when set, only this customer / subscription qualifies
    customer_id = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    subscription_id = Column(GUID(), ForeignKey("subscriptions.id"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("Product", secondary=discount_products)
    redemptions = relationship("DiscountRedemption", back_populates="discount")

    @property
    def product_ids(self):
        ids = [product.id for product in self.products]
        if self.product_id and self.product_id not in ids:
            ids.insert(0, self.product_id)
        return ids


class DiscountRedemption(Base):
    """One row per discount per invoice, so a cancelled invoice can give its use back."""
    __tablename__ = "discount_redemptions"
    __table_args__ = (
        UniqueConstraint("discount_id", "invoice_id", name="uq_redemptions_discount_invoice"),
        CheckConstraint("amount >= 0", name="ck_redemptions_amount"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    discount_id = Column(GUID(), ForeignKey("discounts.id"), nullable=False, index=True)
    invoice_id = Column(GUID(), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    discount = relationship("Discount", back_populates="redemptions")
