from enum import Enum
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel


class Decision(str, Enum):
    ALLOW = "ALLOW"
    CHALLENGE = "CHALLENGE"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class CheckoutContext(BaseModel):
    request_id: UUID
    account_id: Optional[UUID] = None
    ip_address: str
    device_fingerprint: Optional[str] = None
    card_fingerprint: Optional[str] = None
    billing_country: Optional[str] = None
    card_avs_result: Optional[str] = None
    email: Optional[str] = None
    plan_id: UUID
    requested_price: Optional[float] = None
    is_trial: bool = False
    is_trusted_high_volume: bool = False
    idempotency_key: Optional[str] = None
    extra: dict[str, Any] = {}


class RuleVerdict(BaseModel):
    rule_id: str
    decision: Decision
    reason: str
    triggered: bool


class AIVerdict(BaseModel):
    model: str
    score: float
    decision: Decision
    reason: str
    degraded: bool = False


class RiskDecision(BaseModel):
    request_id: UUID
    decision: Decision
    reason: str
    rule_results: list[RuleVerdict]
    ai_results: list[AIVerdict]