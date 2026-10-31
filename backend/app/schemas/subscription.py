import uuid
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator
from app.models.subscription import SubscriptionStatus


class SubscriptionLineCreate(BaseModel):
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    quantity: int = Field(default=1, ge=1)
    # Leave empty to use the plan or product price, including any variant price
    unit_price: Optional[Decimal] = Field(default=None, ge=0)


class SubscriptionLineUpdate(BaseModel):
    quantity: int = Field(ge=1)


class SubscriptionLineOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    quantity: int
    unit_price: Decimal
    tax_amount: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}


class SubscriptionCreate(BaseModel):
    customer_id: uuid.UUID
    # Either plan_id or template_id is required; a template also supplies the lines
    plan_id: Optional[uuid.UUID] = None
    variant_id: Optional[uuid.UUID] = None
    template_id: Optional[uuid.UUID] = None
    start_date: Optional[date] = None
    expiry_date: Optional[date] = None
    payment_terms: Optional[int] = Field(default=None, ge=0)
    lines: List[SubscriptionLineCreate] = []

    @model_validator(mode="after")
    def check_dates(self):
        if self.start_date and self.expiry_date and self.expiry_date < self.start_date:
            raise ValueError("expiry_date cannot be before start_date")
        return self


class SubscriptionUpdate(BaseModel):
    start_date: Optional[date] = None
    expiry_date: Optional[date] = None
    payment_terms: Optional[int] = Field(default=None, ge=0)


class SubscriptionOut(BaseModel):
    id: uuid.UUID
    subscription_number: str
    customer_id: uuid.UUID
    customer_name: Optional[str] = None
    plan_id: uuid.UUID
    plan_name: Optional[str] = None
    variant_id: Optional[uuid.UUID] = None
    template_id: Optional[uuid.UUID] = None
    status: SubscriptionStatus
    start_date: Optional[date] = None
    expiry_date: Optional[date] = None
    quotation_valid_until: Optional[date] = None
    next_billing_date: Optional[date] = None
    payment_terms: int
    created_at: datetime
    lines: List[SubscriptionLineOut] = []

    model_config = {"from_attributes": True}


class SubscriptionHistoryOut(BaseModel):
    from_status: Optional[SubscriptionStatus] = None
    to_status: SubscriptionStatus
    changed_by: Optional[uuid.UUID] = None
    changed_at: datetime

    model_config = {"from_attributes": True}
