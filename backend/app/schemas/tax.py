import uuid
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator
from app.models.tax import TaxAppliesTo


class TaxRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    rate: Decimal = Field(ge=0, le=1, description="0.18 means 18%")
    applies_to: TaxAppliesTo = TaxAppliesTo.all
    product_id: Optional[uuid.UUID] = None
    plan_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def check_target(self):
        if self.applies_to == TaxAppliesTo.product and not self.product_id:
            raise ValueError("A product tax rule needs product_id")
        if self.applies_to == TaxAppliesTo.plan and not self.plan_id:
            raise ValueError("A plan tax rule needs plan_id")
        return self


class TaxRuleUpdate(BaseModel):
    name: Optional[str] = None
    rate: Optional[Decimal] = Field(default=None, ge=0, le=1)
    applies_to: Optional[TaxAppliesTo] = None
    product_id: Optional[uuid.UUID] = None
    plan_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class TaxRuleOut(BaseModel):
    id: uuid.UUID
    name: str
    rate: Decimal
    applies_to: TaxAppliesTo
    product_id: Optional[uuid.UUID] = None
    plan_id: Optional[uuid.UUID] = None
    is_active: bool

    model_config = {"from_attributes": True}

