import uuid
import enum
from datetime import date
from decimal import Decimal
from sqlalchemy import (
    Column, String, Numeric, Date, DateTime, Enum, ForeignKey, Integer, CheckConstraint, Index, text,
)
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
    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="ck_invoices_subtotal"),
        CheckConstraint("tax_total >= 0", name="ck_invoices_tax_total"),
        CheckConstraint("discount_total >= 0", name="ck_invoices_discount_total"),
        CheckConstraint("grand_total >= 0", name="ck_invoices_grand_total"),
        CheckConstraint("amount_paid >= 0", name="ck_invoices_amount_paid"),
        CheckConstraint("period_end >= period_start", name="ck_invoices_period"),
        # One live invoice per subscription per billing period: the database itself
        # refuses double billing. A cancelled invoice frees its period for a reissue.
        Index(
            "uq_invoices_subscription_period",
            "subscription_id",
            "period_start",
            unique=True,
            postgresql_where=text("status <> 'cancelled'"),
            sqlite_where=text("status <> 'cancelled'"),
        ),
        Index("ix_invoices_created_at", "created_at"),
        Index("ix_invoices_status_due_date", "status", "due_date"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    subscription_id = Column(GUID(), ForeignKey("subscriptions.id"), nullable=False, index=True)
    customer_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.draft, nullable=False, index=True)
    due_date = Column(Date, nullable=False, index=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    # Billed-to details are frozen so later profile edits cannot change an issued invoice
    customer_name = Column(String(255), nullable=True)
    customer_email = Column(String(255), nullable=True)
    subtotal = Column(Numeric(12, 2), default=0, nullable=False)
    tax_total = Column(Numeric(12, 2), default=0, nullable=False)
    discount_total = Column(Numeric(12, 2), default=0, nullable=False)
    grand_total = Column(Numeric(12, 2), default=0, nullable=False)
    amount_paid = Column(Numeric(12, 2), default=0, server_default="0", nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")
    subscription = relationship("Subscription")
    customer = relationship("User")

    @property
    def balance_due(self) -> Decimal:
        if self.status == InvoiceStatus.cancelled:
            return Decimal("0.00")
        return Decimal(self.grand_total or 0) - Decimal(self.amount_paid or 0)

    @property
    def is_overdue(self) -> bool:
        return self.status == InvoiceStatus.confirmed and self.due_date < date.today()

    @property
    def subscription_number(self):
        return self.subscription.subscription_number if self.subscription else None


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_invoice_lines_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_invoice_lines_unit_price"),
        CheckConstraint("line_total >= 0", name="ck_invoice_lines_total"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(GUID(), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(GUID(), ForeignKey("products.id"), nullable=True, index=True)
    description = Column(String(500), nullable=True)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), default=0, nullable=False)
    discount = Column(Numeric(12, 2), default=0, nullable=False)
    line_total = Column(Numeric(12, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="lines")
    product = relationship("Product")

