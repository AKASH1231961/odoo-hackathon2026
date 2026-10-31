from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from sqlalchemy.orm import Session
from app.models.discount import Discount, DiscountType, DiscountScope

CENT = Decimal("0.01")


class DiscountEngine:
    """
    Discount application service.
    Eligibility: active, within dates, within usage limits, scope and target match.
    apply() returns the discount amount (not the discounted total).
    price_lines() works out a whole invoice: product discounts per line, subscription
    discounts once on the total, each on what is left so a total never goes below zero.
    One invoice consumes one use of a discount, however many lines it touches.
    """

    def __init__(self, db: Session):
        self.db = db

    def _candidates(self, lock: bool = False):
        today = date.today()
        query = self.db.query(Discount).filter(
            Discount.is_active.is_(True),
            Discount.start_date <= today,
        )
        if lock:
            # Serialises invoices sharing a limited discount so max_uses cannot be overrun
            query = query.with_for_update().populate_existing()
        return query.order_by(Discount.created_at, Discount.id).all()

    def _eligible(self, d, product_id, quantity, amount, customer_id, subscription_id) -> bool:
        today = date.today()
        if d.end_date and d.end_date < today:
            return False
        if d.max_uses is not None and d.used_count >= d.max_uses:
            return False
        if d.min_purchase and Decimal(str(amount)) < Decimal(str(d.min_purchase)):
            return False
        if d.min_quantity and quantity < d.min_quantity:
            return False
        if d.customer_id and d.customer_id != customer_id:
            return False
        if d.subscription_id and d.subscription_id != subscription_id:
            return False
        if d.scope == DiscountScope.product and product_id not in set(d.product_ids):
            return False
        return True

    def get_applicable_discounts(
        self,
        product_id=None,
        quantity: int = 1,
        line_total: Decimal = Decimal("0"),
        customer_id=None,
        subscription_id=None,
    ):
        return [
            d for d in self._candidates()
            if self._eligible(d, product_id, quantity, line_total, customer_id, subscription_id)
        ]

    def apply(self, discount: Discount, line_total: Decimal) -> Decimal:
        line_total = Decimal(str(line_total))
        if discount.type == DiscountType.fixed:
            return min(Decimal(str(discount.value)), line_total)
        # Percentage
        result = line_total * (Decimal(str(discount.value)) / Decimal("100"))
        return result.quantize(CENT, rounding=ROUND_HALF_UP)

    def price_lines(self, lines, customer_id=None, subscription_id=None):
        """
        lines: list of (product_id, quantity, amount).
        Returns (discount per line, {discount: total amount given}).
        """
        remaining = [Decimal(str(amount)) for _, _, amount in lines]
        per_line = [Decimal("0.00") for _ in lines]
        used = {}

        def give(discount, index, amount):
            remaining[index] -= amount
            per_line[index] += amount
            used[discount] = used.get(discount, Decimal("0.00")) + amount

        candidates = self._candidates(lock=True)

        for d in candidates:
            if d.scope != DiscountScope.product:
                continue
            for i, (product_id, quantity, amount) in enumerate(lines):
                if remaining[i] > 0 and self._eligible(
                    d, product_id, quantity, amount, customer_id, subscription_id
                ):
                    give(d, i, self.apply(d, remaining[i]))

        subtotal = sum((Decimal(str(amount)) for _, _, amount in lines), Decimal("0"))
        total_quantity = sum(quantity for _, quantity, _ in lines)
        for d in candidates:
            if d.scope != DiscountScope.subscription:
                continue
            base = sum(remaining, Decimal("0"))
            if base <= 0 or not self._eligible(
                d, None, total_quantity, subtotal, customer_id, subscription_id
            ):
                continue
            # Spread across the lines so each line's tax is on what is really charged
            left = self.apply(d, base)
            indexes = [i for i in range(len(lines)) if remaining[i] > 0]
            shares = [remaining[i] for i in indexes]
            for position, i in enumerate(indexes):
                if position == len(indexes) - 1:
                    share = min(left, remaining[i])
                else:
                    share = (self.apply(d, base) * shares[position] / base).quantize(
                        CENT, rounding=ROUND_HALF_UP
                    )
                    share = min(share, left)
                give(d, i, share)
                left -= share

        return per_line, {d: amount for d, amount in used.items() if amount > 0}

    def mark_used(self, discount: Discount):
        discount.used_count += 1
        if discount.max_uses is not None and discount.used_count >= discount.max_uses:
            discount.is_active = False
        self.db.add(discount)

    def release(self, discount: Discount):
        """Give back one use when the invoice that consumed it is cancelled."""
        was_exhausted = discount.max_uses is not None and discount.used_count >= discount.max_uses
        discount.used_count = max(discount.used_count - 1, 0)
        if was_exhausted and not (discount.end_date and discount.end_date < date.today()):
            discount.is_active = True
        self.db.add(discount)
