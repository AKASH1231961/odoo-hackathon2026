from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from sqlalchemy.orm import Session
from app.models.discount import Discount, DiscountType, DiscountScope


class DiscountEngine:
    """
    Discount application service.
    Eligibility: active, within dates, within usage limits, scope match.
    apply() returns the discount amount (not the discounted total).
    mark_used() atomically increments used_count and auto-deactivates on exhaustion.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_applicable_discounts(
        self,
        product_id=None,
        quantity: int = 1,
        line_total: Decimal = Decimal("0"),
    ):
        today = date.today()
        candidates = (
            self.db.query(Discount)
            .filter(
                Discount.is_active.is_(True),
                Discount.start_date <= today,
            )
            .all()
        )

        applicable = []
        for d in candidates:
            # Date expiry
            if d.end_date and d.end_date < today:
                continue
            # Usage limit
            if d.max_uses is not None and d.used_count >= d.max_uses:
                continue
            # Min purchase
            if d.min_purchase and Decimal(str(line_total)) < Decimal(str(d.min_purchase)):
                continue
            # Min quantity
            if d.min_quantity and quantity < d.min_quantity:
                continue
            # Scope: product-scoped must match product_id
            if d.scope == DiscountScope.product:
                if d.product_id != product_id:
                    continue
            applicable.append(d)

        return applicable

    def apply(self, discount: Discount, line_total: Decimal) -> Decimal:
        line_total = Decimal(str(line_total))
        if discount.type == DiscountType.fixed:
            return min(Decimal(str(discount.value)), line_total)
        # Percentage
        result = line_total * (Decimal(str(discount.value)) / Decimal("100"))
        return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def mark_used(self, discount: Discount):
        discount.used_count += 1
        if discount.max_uses is not None and discount.used_count >= discount.max_uses:
            discount.is_active = False
        self.db.add(discount)

