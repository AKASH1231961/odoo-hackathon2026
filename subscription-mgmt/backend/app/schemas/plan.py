import uuid
from typing import Optional
from datetime import date
from decimal import Decimal
from pydantic import BaseModel
from app.models.plan import BillingInterval


class PlanCreate(BaseModel):
    name: str
    product_id: uuid.UUID
    billing_interval: BillingInterval
    price: Decimal
    min_quantity: int = 1
    available_from: Optional[date] = None
    available_to: Optional[date] = None
    auto_close: bool = False
    can_pause: bool = True
    can_close_early: bool = True
    can_renew: bool = True


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[Decimal] = None
    available_to: Optional[date] = None
    auto_close: Optional[bool] = None
    can_pause: Optional[bool] = None
    can_close_early: Optional[bool] = None
    can_renew: Optional[bool] = None
    is_active: Optional[bool] = None


class PlanOut(BaseModel):
    id: uuid.UUID
    name: str
    product_id: uuid.UUID
    billing_interval: BillingInterval
    price: Decimal
    min_quantity: int
    available_from: Optional[date] = None
    available_to: Optional[date] = None
    auto_close: bool
    can_pause: bool
    can_close_early: bool
    can_renew: bool
    is_active: bool

    model_config = {"from_attributes": True}

