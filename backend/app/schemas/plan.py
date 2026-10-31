import uuid
from typing import Optional
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator
from app.models.plan import BillingInterval


class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    product_id: uuid.UUID
    billing_interval: BillingInterval
    price: Decimal = Field(ge=0)
    min_quantity: int = Field(default=1, ge=1)
    available_from: Optional[date] = None
    available_to: Optional[date] = None
    auto_close: bool = False
    can_pause: bool = True
    can_close_early: bool = True
    can_renew: bool = True

    @model_validator(mode="after")
    def check_dates(self):
        if self.available_from and self.available_to and self.available_to < self.available_from:
            raise ValueError("available_to cannot be before available_from")
        return self


class PlanUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    price: Optional[Decimal] = Field(default=None, ge=0)
    min_quantity: Optional[int] = Field(default=None, ge=1)
    available_from: Optional[date] = None
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

