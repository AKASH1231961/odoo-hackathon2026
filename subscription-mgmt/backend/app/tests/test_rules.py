import fakeredis
import pytest
from uuid import uuid4

from app.isse.schemas import CheckoutContext, Decision
from app.isse.rules import velocity, integrity


@pytest.fixture(autouse=True)
def patch_redis(monkeypatch):
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(velocity, "_redis", fake)
    monkeypatch.setattr(integrity, "_redis", fake)
    yield fake


def _ctx(**overrides) -> CheckoutContext:
    base = dict(request_id=uuid4(), ip_address="1.2.3.4", plan_id=uuid4())
    base.update(overrides)
    return CheckoutContext(**base)


def test_signup_velocity_blocks_after_limit():
    ctx = _ctx(extra={"is_signup": True})
    for _ in range(5):
        assert velocity.check_signup_velocity(ctx).decision == Decision.ALLOW

    result = velocity.check_signup_velocity(ctx)
    assert result.decision == Decision.BLOCK
    assert result.triggered


def test_idempotency_blocks_duplicate_requests():
    ctx = _ctx(idempotency_key="abc-123")
    assert integrity.check_idempotency(ctx).decision == Decision.ALLOW
    assert integrity.check_idempotency(ctx).decision == Decision.BLOCK