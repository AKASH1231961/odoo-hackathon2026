import uuid
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class TemplateLineCreate(BaseModel):
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    quantity: int = Field(default=1, ge=1)
    unit_price: Optional[Decimal] = Field(default=None, ge=0)


class TemplateLineOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    quantity: int
    unit_price: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class QuotationTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    plan_id: uuid.UUID
    validity_days: int = Field(default=30, ge=1)
    payment_terms: int = Field(default=15, ge=0)
    notes: Optional[str] = None
    lines: List[TemplateLineCreate] = []


class QuotationTemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    validity_days: Optional[int] = Field(default=None, ge=1)
    payment_terms: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None
    lines: Optional[List[TemplateLineCreate]] = None


class QuotationTemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    plan_id: uuid.UUID
    validity_days: int
    payment_terms: int
    notes: Optional[str] = None
    created_at: datetime
    lines: List[TemplateLineOut] = []

    model_config = {"from_attributes": True}
