"""Tests for subscription state machine transitions."""
import uuid
import pytest
from datetime import date
from app.models.subscription import (
    Subscription,
    SubscriptionStatus,
    SubscriptionStatusHistory,
)
from app.models.plan import Plan, BillingInterval
from app.models.product import Product
from app.models.user import User, UserRole
from app.services.subscription_service import SubscriptionService
from app.core.security import hash_password
from decimal import Decimal


def _seed(db):
    product = Product(id=uuid.uuid4(), name="P", sales_price=Decimal("100"))
    db.add(product)
    plan = Plan(
        id=uuid.uuid4(), name="Monthly", product_id=product.id,
        billing_interval=BillingInterval.monthly, price=Decimal("100"),
        can_pause=True, can_close_early=True, can_renew=True,
    )
    db.add(plan)
    customer = User(
        id=uuid.uuid4(), email=f"c{uuid.uuid4()}@example.com",
        password_hash=hash_password("Test@1234"), role=UserRole.customer,
    )
    db.add(customer)
    db.flush()
    sub = Subscription(
        id=uuid.uuid4(), subscription_number=f"SUB-TEST-{uuid.uuid4().hex[:5]}",
        customer_id=customer.id, plan_id=plan.id,
        status=SubscriptionStatus.draft, payment_terms=15,
    )
    db.add(sub)
    db.flush()
    return sub


def test_confirm_from_quotation(db):
    sub = _seed(db)
    svc = SubscriptionService(db)
    svc.send_to_quotation(sub.id)
    result = svc.confirm(sub.id)
    assert result.status == SubscriptionStatus.confirmed
    history = (
        db.query(SubscriptionStatusHistory)
        .filter(
            SubscriptionStatusHistory.subscription_id == sub.id,
            SubscriptionStatusHistory.to_status == SubscriptionStatus.confirmed,
        )
        .one()
    )
    assert history.from_status == SubscriptionStatus.quotation


def test_draft_cannot_skip_quotation(db):
    from fastapi import HTTPException
    sub = _seed(db)
    with pytest.raises(HTTPException) as exc_info:
        SubscriptionService(db).confirm(sub.id)
    assert exc_info.value.status_code == 400


def test_activate_from_confirmed(db):
    sub = _seed(db)
    svc = SubscriptionService(db)
    svc.send_to_quotation(sub.id)
    svc.confirm(sub.id)
    result = svc.activate(sub.id)
    assert result.status == SubscriptionStatus.active
    assert result.start_date == date.today()


def test_pause_active(db):
    sub = _seed(db)
    svc = SubscriptionService(db)
    svc.send_to_quotation(sub.id)
    svc.confirm(sub.id)
    svc.activate(sub.id)
    result = svc.pause(sub.id)
    assert result.status == SubscriptionStatus.paused


def test_resume_paused(db):
    sub = _seed(db)
    svc = SubscriptionService(db)
    svc.send_to_quotation(sub.id)
    svc.confirm(sub.id)
    svc.activate(sub.id)
    svc.pause(sub.id)
    result = svc.resume(sub.id)
    assert result.status == SubscriptionStatus.active


def test_close_active(db):
    sub = _seed(db)
    svc = SubscriptionService(db)
    svc.send_to_quotation(sub.id)
    svc.confirm(sub.id)
    svc.activate(sub.id)
    result = svc.close(sub.id)
    assert result.status == SubscriptionStatus.closed


def test_renew_closed(db):
    sub = _seed(db)
    svc = SubscriptionService(db)
    svc.send_to_quotation(sub.id)
    svc.confirm(sub.id)
    svc.activate(sub.id)
    svc.close(sub.id)
    result = svc.renew(sub.id)
    assert result.status == SubscriptionStatus.active


def test_invalid_transition_raises(db):
    from fastapi import HTTPException
    sub = _seed(db)
    svc = SubscriptionService(db)
    with pytest.raises(HTTPException) as exc_info:
        svc.activate(sub.id)  # draft → activate without confirm
    assert exc_info.value.status_code == 400
