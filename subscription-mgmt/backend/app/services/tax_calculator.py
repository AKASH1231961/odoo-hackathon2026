from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from app.models.tax import TaxRule, TaxAppliesTo


class TaxCalculator:
    """
    Tax calculation service.
    Priority: product-specific rule → global (applies_to=all) rule → 0 tax.
    """

    def __init__(self, db: Session):
        self.db = db

    def calculate(self, product_id, line_total: Decimal) -> Decimal:
        line_total = Decimal(str(line_total))

        # 1. Try product-specific rule first
        rule = (
            self.db.query(TaxRule)
            .filter(
                TaxRule.is_active.is_(True),
                TaxRule.applies_to == TaxAppliesTo.product,
                TaxRule.product_id == product_id,
            )
            .first()
        )

        # 2. Fall back to global rule
        if not rule:
            rule = (
                self.db.query(TaxRule)
                .filter(
                    TaxRule.is_active.is_(True),
                    TaxRule.applies_to == TaxAppliesTo.all,
                )
                .first()
            )

        # 3. No rule → no tax
        if not rule:
            return Decimal("0.00")

        # 4. Apply rate and round
        tax = line_total * Decimal(str(rule.rate))
        return tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

