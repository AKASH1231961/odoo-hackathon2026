import uuid
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel
from app.models.discount import DiscountType, DiscountScope


class DiscountCreate(BaseModel):
    name: str
    type: DiscountType
    value: Decimal
    min_purchase: Optional[Decimal] = None
    min_quantity: Optional[int] = None
    start_date: date
    end_date: Optional[date] = None
    max_uses: Optional[int] = None
    scope: DiscountScope
    product_id: Optional[uuid.UUID] = None


class DiscountUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[Decimal] = None
    end_date: Optional[date] = None
    max_uses: Optional[int] = None
    is_active: Optional[bool] = None


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
    is_active: bool

    model_config = {"from_attributes": True}

