"""Tests for DiscountEngine — fixed, percentage, expiry, usage limits, scope."""
from decimal import Decimal
from datetime import date, timedelta
import uuid
import pytest
from app.services.discount_engine import DiscountEngine
from app.models.discount import Discount, DiscountType, DiscountScope
from app.models.product import Product


def _make_discount(db, **kwargs):
    defaults = dict(
        id=uuid.uuid4(),
        name="Test Discount",
        type=DiscountType.percentage,
        value=Decimal("10"),
        start_date=date.today() - timedelta(days=1),
        scope=DiscountScope.subscription,
        is_active=True,
        used_count=0,
    )
    defaults.update(kwargs)
    d = Discount(**defaults)
    db.add(d)
    db.flush()
    return d


def test_percentage_discount(db):
    _make_discount(db, value=Decimal("10"))
    engine = DiscountEngine(db)
    applicable = engine.get_applicable_discounts(line_total=Decimal("1000"))
    assert len(applicable) >= 1
    amount = engine.apply(applicable[0], Decimal("1000"))
    assert amount == Decimal("100.00")


def test_fixed_discount(db):
    _make_discount(db, type=DiscountType.fixed, value=Decimal("50"))
    engine = DiscountEngine(db)
    applicable = engine.get_applicable_discounts(line_total=Decimal("1000"))
    assert len(applicable) >= 1
    fixed = [a for a in applicable if a.type == DiscountType.fixed][0]
    amount = engine.apply(fixed, Decimal("1000"))
    assert amount == Decimal("50")


def test_expired_discount_not_applied(db):
    _make_discount(db, end_date=date.today() - timedelta(days=1))
    engine = DiscountEngine(db)
    applicable = engine.get_applicable_discounts(line_total=Decimal("1000"))
    expired = [a for a in applicable if a.end_date and a.end_date < date.today()]
    assert len(expired) == 0


def test_usage_limit_exhausted(db):
    d = _make_discount(db, max_uses=5, used_count=5)
    engine = DiscountEngine(db)
    applicable = engine.get_applicable_discounts(line_total=Decimal("1000"))
    assert d not in applicable


def test_mark_used_deactivates_on_exhaustion(db):
    d = _make_discount(db, max_uses=1, used_count=0)
    engine = DiscountEngine(db)
    engine.mark_used(d)
    db.flush()
    assert d.used_count == 1
    assert d.is_active is False


def test_min_purchase_not_met(db):
    d = _make_discount(db, min_purchase=Decimal("500"))
    engine = DiscountEngine(db)
    applicable = engine.get_applicable_discounts(line_total=Decimal("100"))
    assert d not in applicable


def test_product_scope_mismatch(db):
    product = Product(name="Product", sales_price=Decimal("100"))
    db.add(product)
    db.flush()
    d = _make_discount(db, scope=DiscountScope.product, product_id=product.id)
    engine = DiscountEngine(db)
    # Query with a different product_id
    applicable = engine.get_applicable_discounts(product_id=uuid.uuid4(), line_total=Decimal("1000"))
    assert d not in applicable


def test_product_scope_matches_associated_product(db):
    product = Product(name="Product", sales_price=Decimal("100"))
    db.add(product)
    db.flush()
    discount = _make_discount(db, scope=DiscountScope.product)
    discount.products = [product]
    db.flush()

    applicable = DiscountEngine(db).get_applicable_discounts(
        product_id=product.id,
        line_total=Decimal("1000"),
    )
    assert discount in applicable
