import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class QuotationTemplateCreate(BaseModel):
    name: str
    plan_id: uuid.UUID
    validity_days: int = 30
    notes: Optional[str] = None


class QuotationTemplateUpdate(BaseModel):
    name: Optional[str] = None
    validity_days: Optional[int] = None
    notes: Optional[str] = None


class QuotationTemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    plan_id: uuid.UUID
    validity_days: int
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

