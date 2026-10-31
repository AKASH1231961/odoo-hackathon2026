import uuid
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator
from app.models.discount import DiscountType, DiscountScope


class DiscountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: DiscountType
    value: Decimal = Field(gt=0)
    min_purchase: Optional[Decimal] = Field(default=None, ge=0)
    min_quantity: Optional[int] = Field(default=None, ge=1)
    start_date: date
    end_date: Optional[date] = None
    max_uses: Optional[int] = Field(default=None, ge=1)
    scope: DiscountScope
    product_id: Optional[uuid.UUID] = None
    product_ids: List[uuid.UUID] = Field(default_factory=list)
    customer_id: Optional[uuid.UUID] = None
    subscription_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def check_rules(self):
        if self.type == DiscountType.percentage and self.value > 100:
            raise ValueError("A percentage discount cannot be more than 100")
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class DiscountUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[Decimal] = Field(default=None, gt=0)
    min_purchase: Optional[Decimal] = Field(default=None, ge=0)
    min_quantity: Optional[int] = Field(default=None, ge=1)
    end_date: Optional[date] = None
    max_uses: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None
    product_ids: Optional[List[uuid.UUID]] = None


class DiscountOut(BaseModel):
    id: uuid.UUID
    name: str
    type: DiscountType
    value: Decimal
    min_purchase: Optional[Decimal] = None
    min_quantity: Optional[int] = None
    start_date: date
    end_date: Optional[date] = None
    max_uses: Optional[int] = None
    used_count: int
    scope: DiscountScope
    product_id: Optional[uuid.UUID] = None
    product_ids: List[uuid.UUID] = Field(default_factory=list)
    customer_id: Optional[uuid.UUID] = None
    subscription_id: Optional[uuid.UUID] = None
    is_active: bool

    model_config = {"from_attributes": True}
