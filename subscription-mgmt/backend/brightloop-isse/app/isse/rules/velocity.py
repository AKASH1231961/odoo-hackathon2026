import time
from uuid import uuid4
import redis
from app.isse.config import settings
from app.isse.schemas import CheckoutContext, RuleVerdict, Decision

_redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def _sliding_window_count(key: str, window_sec: int) -> int:
    """Redis sorted-set based sliding window counter (accurate, not fixed-bucket)."""
    now = time.time()
    pipe = _redis.pipeline()
    pipe.zremrangebyscore(key, 0, now - window_sec)
    pipe.zadd(key, {uuid4().hex: now})
    pipe.zcard(key)
    pipe.expire(key, window_sec)
    _, _, count, _ = pipe.execute()
    return count


def check_signup_velocity(ctx: CheckoutContext) -> RuleVerdict:
    if not ctx.extra.get("is_signup"):
        return RuleVerdict(rule_id="VELOCITY_SIGNUP", decision=Decision.ALLOW,
                            reason="not_a_signup_event", triggered=False)

    key = f"isse:velocity:signup:{ctx.ip_address}"
    count = _sliding_window_count(key, settings.signup_velocity_window_sec)

    if count > settings.signup_velocity_limit:
        return RuleVerdict(rule_id="VELOCITY_SIGNUP", decision=Decision.BLOCK,
                            reason=f"ip_signup_velocity_exceeded:{count}", triggered=True)
    return RuleVerdict(rule_id="VELOCITY_SIGNUP", decision=Decision.ALLOW,
                        reason="within_limit", triggered=False)


def check_card_attempt_velocity(ctx: CheckoutContext) -> RuleVerdict:
    if not ctx.card_fingerprint:
        return RuleVerdict(rule_id="VELOCITY_CARD_ATTEMPT", decision=Decision.ALLOW,
                            reason="no_card_fingerprint", triggered=False)

    key = f"isse:velocity:card:{ctx.card_fingerprint}"
    count = _sliding_window_count(key, settings.card_attempt_velocity_window_sec)

    if count > settings.card_attempt_velocity_limit:
        return RuleVerdict(rule_id="VELOCITY_CARD_ATTEMPT", decision=Decision.CHALLENGE,
                            reason=f"card_attempt_velocity_exceeded:{count}", triggered=True)
    return RuleVerdict(rule_id="VELOCITY_CARD_ATTEMPT", decision=Decision.ALLOW,
                        reason="within_limit", triggered=False)


def check_api_rate_limit(api_key: str, limit_per_min: int | None = None) -> RuleVerdict:
    limit = limit_per_min or settings.api_default_rate_limit_per_min
    key = f"isse:velocity:apikey:{api_key}"
    count = _sliding_window_count(key, 60)

    if count > limit:
        return RuleVerdict(rule_id="VELOCITY_API_KEY", decision=Decision.BLOCK,
                            reason=f"api_rate_limit_exceeded:{count}/{limit}", triggered=True)
    return RuleVerdict(rule_id="VELOCITY_API_KEY", decision=Decision.ALLOW,
                        reason="within_limit", triggered=False)