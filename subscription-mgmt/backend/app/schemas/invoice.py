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
    status: InvoiceStatus
    due_date: date
    subtotal: Decimal
    tax_total: Decimal
    discount_total: Decimal
    grand_total: Decimal
    issued_at: Optional[datetime] = None
    created_at: datetime
    lines: List[InvoiceLineOut] = []

    model_config = {"from_attributes": True}

