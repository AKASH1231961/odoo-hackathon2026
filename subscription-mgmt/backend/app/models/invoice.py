import uuid
import enum
from sqlalchemy import Column, String, Numeric, Date, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.types import GUID


class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"
    paid = "paid"
    cancelled = "cancelled"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    subscription_id = Column(GUID(), ForeignKey("subscriptions.id"), nullable=False, index=True)
    customer_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.draft, nullable=False, index=True)
    due_date = Column(Date, nullable=False, index=True)
    subtotal = Column(Numeric(12, 2), default=0, nullable=False)
    tax_total = Column(Numeric(12, 2), default=0, nullable=False)
    discount_total = Column(Numeric(12, 2), default=0, nullable=False)
    grand_total = Column(Numeric(12, 2), default=0, nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")
    subscription = relationship("Subscription")
    customer = relationship("User")


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(GUID(), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(GUID(), ForeignKey("products.id"), nullable=True)
    description = Column(String(500), nullable=True)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), default=0, nullable=False)
    discount = Column(Numeric(12, 2), default=0, nullable=False)
    line_total = Column(Numeric(12, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="lines")
    product = relationship("Product")

