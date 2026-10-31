"""Tests for TaxCalculator — all rule combination paths."""
from decimal import Decimal
import pytest
from app.services.tax_calculator import TaxCalculator
from app.models.tax import TaxRule, TaxAppliesTo
from app.core.types import GUID
import uuid


def _add_rule(db, name, rate, applies_to, product_id=None):
    rule = TaxRule(
        id=uuid.uuid4(),
        name=name,
        rate=Decimal(str(rate)),
        applies_to=applies_to,
        product_id=product_id,
        is_active=True,
    )
    db.add(rule)
    db.flush()
    return rule


def test_global_rule_applied(db):
    _add_rule(db, "GST 18%", "0.1800", TaxAppliesTo.all)
    calc = TaxCalculator(db)
    result = calc.calculate(product_id=uuid.uuid4(), line_total=Decimal("1000"))
    assert result == Decimal("180.00")


def test_product_rule_overrides_global(db):
    product_id = uuid.uuid4()
    _add_rule(db, "GST 18%", "0.1800", TaxAppliesTo.all)
    _add_rule(db, "Special 5%", "0.0500", TaxAppliesTo.product, product_id=product_id)
    calc = TaxCalculator(db)
    result = calc.calculate(product_id=product_id, line_total=Decimal("1000"))
    assert result == Decimal("50.00")


def test_no_rule_returns_zero(db):
    calc = TaxCalculator(db)
    result = calc.calculate(product_id=uuid.uuid4(), line_total=Decimal("1000"))
    assert result == Decimal("0.00")


def test_rounding(db):
    _add_rule(db, "GST 18.5%", "0.1850", TaxAppliesTo.all)
    calc = TaxCalculator(db)
    # 100 * 0.185 = 18.5 → should round to 18.50
    result = calc.calculate(product_id=uuid.uuid4(), line_total=Decimal("100"))
    assert result == Decimal("18.50")

