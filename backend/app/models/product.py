import uuid
from sqlalchemy import Column, String, Numeric, Boolean, DateTime, Text, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.types import GUID


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("sales_price >= 0", name="ck_products_sales_price"),
        CheckConstraint("cost_price >= 0", name="ck_products_cost_price"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=True)
    sales_price = Column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    cost_price = Column(Numeric(12, 2), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    product_id = Column(GUID(), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(255), nullable=False)
    price_delta = Column(Numeric(12, 2), default=0, server_default="0", nullable=False)
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)

    product = relationship("Product", back_populates="variants")

