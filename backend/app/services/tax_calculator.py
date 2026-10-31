from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from app.models.tax import TaxRule, TaxAppliesTo


class TaxCalculator:
    """
    Tax calculation service.
    Priority: product rule → plan rule → global (applies_to=all) rule → 0 tax.
    """

    def __init__(self, db: Session):
        self.db = db

    def _rule(self, *criteria):
        return (
            self.db.query(TaxRule)
            .filter(TaxRule.is_active.is_(True), *criteria)
            .order_by(TaxRule.created_at.desc(), TaxRule.id)
            .first()
        )

    def calculate(self, product_id, line_total: Decimal, plan_id=None) -> Decimal:
        line_total = Decimal(str(line_total))

        rule = self._rule(TaxRule.applies_to == TaxAppliesTo.product, TaxRule.product_id == product_id)
        if not rule and plan_id:
            rule = self._rule(TaxRule.applies_to == TaxAppliesTo.plan, TaxRule.plan_id == plan_id)
        if not rule:
            rule = self._rule(TaxRule.applies_to == TaxAppliesTo.all)
        if not rule:
            return Decimal("0.00")

        tax = line_total * Decimal(str(rule.rate))
        return tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
