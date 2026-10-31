import uuid
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel
from app.models.subscription import SubscriptionStatus


class SubscriptionLineCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = 1
    unit_price: Decimal


class SubscriptionLineOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    unit_price: Decimal
    tax_amount: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}


class SubscriptionCreate(BaseModel):
    customer_id: uuid.UUID
    plan_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    template_id: Optional[uuid.UUID] = None
    start_date: Optional[date] = None
    expiry_date: Optional[date] = None
    payment_terms: int = 15
    lines: List[SubscriptionLineCreate] = []


class SubscriptionUpdate(BaseModel):
    start_date: Optional[date] = None
    expiry_date: Optional[date] = None
    payment_terms: Optional[int] = None


class SubscriptionOut(BaseModel):
    id: uuid.UUID
    subscription_number: str
    customer_id: uuid.UUID
    plan_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    status: SubscriptionStatus
    start_date: Optional[date] = None
    expiry_date: Optional[date] = None
    next_billing_date: Optional[date] = None
    payment_terms: int
    created_at: datetime
    lines: List[SubscriptionLineOut] = []

    model_config = {"from_attributes": True}

