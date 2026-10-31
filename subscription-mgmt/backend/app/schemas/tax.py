import uuid
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel
from app.models.tax import TaxAppliesTo


class TaxRuleCreate(BaseModel):
    name: str
    rate: Decimal
    applies_to: TaxAppliesTo = TaxAppliesTo.all
    product_id: Optional[uuid.UUID] = None


class TaxRuleUpdate(BaseModel):
    name: Optional[str] = None
    rate: Optional[Decimal] = None
    applies_to: Optional[TaxAppliesTo] = None
    product_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class TaxRuleOut(BaseModel):
    id: uuid.UUID
    name: str
    rate: Decimal
    applies_to: TaxAppliesTo
    product_id: Optional[uuid.UUID] = None
    is_active: bool

    model_config = {"from_attributes": True}

