import uuid
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from app.models.payment import PaymentMethod


class PaymentCreate(BaseModel):
    invoice_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: PaymentMethod
    payment_date: date
    reference: Optional[str] = None
    note: Optional[str] = None


class PaymentUpdate(BaseModel):
    amount: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    method: Optional[PaymentMethod] = None
    payment_date: Optional[date] = None
    reference: Optional[str] = None
    note: Optional[str] = None


class PaymentOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Decimal
    method: PaymentMethod
    payment_date: date
    reference: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

