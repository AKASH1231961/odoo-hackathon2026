import uuid
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel
from app.models.invoice import InvoiceStatus


class InvoiceLineOut(BaseModel):
    id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    quantity: int
    unit_price: Decimal
    tax_amount: Decimal
    discount: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}


class InvoiceOut(BaseModel):
    id: uuid.UUID
    invoice_number: str
    subscription_id: uuid.UUID
    customer_id: uuid.UUID
    subscription_number: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    status: InvoiceStatus
    due_date: date
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    subtotal: Decimal
    tax_total: Decimal
    discount_total: Decimal
    grand_total: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    is_overdue: bool
    issued_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    lines: List[InvoiceLineOut] = []

    model_config = {"from_attributes": True}

