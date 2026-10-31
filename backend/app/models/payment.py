import uuid
import enum
from sqlalchemy import Column, String, Numeric, Date, DateTime, Enum, ForeignKey, Text, CheckConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.types import GUID


class PaymentMethod(str, enum.Enum):
    cash = "cash"
    bank_transfer = "bank_transfer"
    card = "card"
    upi = "upi"
    other = "other"


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount"),
        Index("ix_payments_payment_date", "payment_date"),
        Index("ix_payments_created_at", "created_at"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(GUID(), ForeignKey("invoices.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    method = Column(Enum(PaymentMethod), nullable=False)
    payment_date = Column(Date, nullable=False)
    reference = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)
    recorded_by = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", back_populates="payments")
    recorder = relationship("User", foreign_keys=[recorded_by])

