from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.subscription import Subscription
from app.models.invoice import Invoice, InvoiceLine, InvoiceStatus
from app.services.numbering import generate_invoice_number
from app.services.tax_calculator import TaxCalculator
from app.services.discount_engine import DiscountEngine
from app.services.interval import next_billing_date_for


class AlreadyBilledError(Exception):
    """Raised when an invoice already exists for the current billing period."""
    pass


class _FakeLine:
    """
    Synthetic line used when a subscription has no explicit subscription_lines.
    Bills the plan's base price directly as the default recurring charge.
    """
    def __init__(self, product_id, unit_price, quantity, product):
        self.product_id = product_id
        self.unit_price = unit_price
        self.quantity = quantity
        self.product = product


class InvoicingService:
    """
    Core invoicing engine.
    Responsibilities:
      - Idempotency check (no double billing per period)
      - Invoice + line creation with automatic tax + discount application
      - Grand total computation
      - Advances next_billing_date on the subscription
    """

    def __init__(self, db: Session):
        self.db = db

    def invoice_exists_for_current_period(self, subscription_id) -> bool:
        """Check if an invoice was already generated today for this subscription."""
        today = date.today()
        existing = (
            self.db.query(Invoice)
            .filter(
                Invoice.subscription_id == subscription_id,
                Invoice.created_at >= today,
            )
            .first()
        )
        return existing is not None

    def generate_for_subscription(self, subscription_id) -> Invoice:
        sub = self.db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not sub:
            raise ValueError("Subscription not found")

        if self.invoice_exists_for_current_period(subscription_id):
            raise AlreadyBilledError(
                f"Invoice already generated today for subscription {sub.subscription_number}"
            )

        invoice = Invoice(
            invoice_number=generate_invoice_number(self.db),
            subscription_id=sub.id,
            customer_id=sub.customer_id,
            status=InvoiceStatus.draft,
            due_date=date.today() + timedelta(days=sub.payment_terms or 15),
        )

        subtotal = Decimal("0")
        tax_total = Decimal("0")
        discount_total = Decimal("0")

        tax_calc = TaxCalculator(self.db)
        discount_engine = DiscountEngine(self.db)

        # Use explicit subscription lines if present, else fall back to plan price
        lines_source = sub.lines if sub.lines else [
            _FakeLine(
                product_id=sub.plan.product_id,
                unit_price=sub.plan.price,
                quantity=sub.plan.min_quantity or 1,
                product=sub.plan.product,
            )
        ]

        for line in lines_source:
            unit_price = Decimal(str(line.unit_price))
            quantity = line.quantity or 1
            line_total = unit_price * quantity

            # Tax — product-specific first, then global fallback
            tax_amount = tax_calc.calculate(line.product_id, line_total)

            # Discounts — auto-applied, no manual step required
            applicable = discount_engine.get_applicable_discounts(
                product_id=line.product_id,
                quantity=quantity,
                line_total=line_total,
            )
            discount_amount = Decimal("0")
            for d in applicable:
                discount_amount += discount_engine.apply(d, line_total)
                discount_engine.mark_used(d)

            final_line_total = line_total + tax_amount - discount_amount

            invoice.lines.append(
                InvoiceLine(
                    product_id=line.product_id,
                    description=getattr(line.product, "name", "Subscription charge"),
                    quantity=quantity,
                    unit_price=unit_price,
                    tax_amount=tax_amount,
                    discount=discount_amount,
                    line_total=final_line_total,
                )
            )

            subtotal += line_total
            tax_total += tax_amount
            discount_total += discount_amount

        invoice.subtotal = subtotal
        invoice.tax_total = tax_total
        invoice.discount_total = discount_total
        invoice.grand_total = subtotal + tax_total - discount_total

        self.db.add(invoice)

        # Advance next_billing_date for the subscription
        sub.next_billing_date = next_billing_date_for(
            sub.plan.billing_interval, date.today()
        )
        self.db.add(sub)

        self.db.commit()
        self.db.refresh(invoice)
        return invoice

