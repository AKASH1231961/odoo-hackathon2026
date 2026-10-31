import redis
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.isse.config import settings
from app.isse.schemas import CheckoutContext, RuleVerdict, Decision

_redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
IDEMPOTENCY_TTL_SEC = 86400


def check_price_integrity(ctx: CheckoutContext, db: Session) -> RuleVerdict:
    plan = db.execute(
        text("SELECT base_price FROM plans WHERE id = :pid"),
        {"pid": str(ctx.plan_id)},
    ).first()

    if plan is None:
        return RuleVerdict(rule_id="PRICE_INTEGRITY", decision=Decision.BLOCK,
                            reason="plan_not_found", triggered=True)

    base_price = float(plan.base_price)

    if ctx.requested_price is not None and abs(ctx.requested_price - base_price) > 0.01:
        return RuleVerdict(rule_id="PRICE_INTEGRITY", decision=Decision.BLOCK,
                            reason=f"price_tamper_detected requested={ctx.requested_price} actual={base_price}",
                            triggered=True)

    return RuleVerdict(rule_id="PRICE_INTEGRITY", decision=Decision.ALLOW,
                        reason="price_matches_plan_snapshot", triggered=False)


def check_idempotency(ctx: CheckoutContext) -> RuleVerdict:
    if not ctx.idempotency_key:
        return RuleVerdict(rule_id="IDEMPOTENCY", decision=Decision.ALLOW,
                            reason="no_idempotency_key_supplied", triggered=False)

    key = f"isse:idempotency:{ctx.idempotency_key}"
    was_set = _redis.set(key, "1", nx=True, ex=IDEMPOTENCY_TTL_SEC)

    if not was_set:
        return RuleVerdict(rule_id="IDEMPOTENCY", decision=Decision.BLOCK,
                            reason="duplicate_request_detected", triggered=True)

    return RuleVerdict(rule_id="IDEMPOTENCY", decision=Decision.ALLOW,
                        reason="first_occurrence", triggered=False)