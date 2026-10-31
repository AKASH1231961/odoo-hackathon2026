import uuid
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel


class ProductVariantCreate(BaseModel):
    label: str
    price_delta: Decimal = Decimal("0")


class ProductVariantOut(BaseModel):
    id: uuid.UUID
    label: str
    price_delta: Decimal
    is_active: bool

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str
    type: Optional[str] = None
    sales_price: Decimal
    cost_price: Optional[Decimal] = None
    notes: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    sales_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ProductOut(BaseModel):
    id: uuid.UUID
    name: str
    type: Optional[str] = None
    sales_price: Decimal
    cost_price: Optional[Decimal] = None
    notes: Optional[str] = None
    is_active: bool
    variants: List[ProductVariantOut] = []

    model_config = {"from_attributes": True}

