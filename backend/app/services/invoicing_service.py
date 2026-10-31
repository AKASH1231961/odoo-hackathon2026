from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.discount import DiscountRedemption
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.invoice import Invoice, InvoiceLine, InvoiceStatus
from app.services.numbering import generate_invoice_number
from app.services.tax_calculator import TaxCalculator
from app.services.discount_engine import DiscountEngine
from app.services.interval import next_billing_date_for


class AlreadyBilledError(Exception):
    """Raised when the subscription has nothing due right now."""
    pass


class NotBillableError(Exception):
    """Raised when the subscription's state does not allow billing."""
    pass


class _FakeLine:
    """
    Synthetic line used when a subscription has no explicit subscription_lines.
    Bills the plan's base price directly as the default recurring charge.
    """
    def __init__(self, product_id, unit_price, quantity, product, variant=None):
        self.product_id = product_id
        self.unit_price = unit_price
        self.quantity = quantity
        self.product = product
        self.variant = variant


class InvoicingService:
    """
    Core invoicing engine.
    Responsibilities:
      - One invoice per billing period, guarded by a row lock and a unique index
      - Invoice + line creation with automatic tax + discount application
      - Grand total computation
      - Advances next_billing_date on the subscription, keeping the billing day
      - Confirm / cancel transitions
    """

    def __init__(self, db: Session):
        self.db = db

    def _next_period(self, sub: Subscription, reissue: bool):
        """Return (period_start, advances_schedule) or raise when nothing can be billed."""
        if reissue:
            last = (
                self.db.query(Invoice)
                .filter(Invoice.subscription_id == sub.id, Invoice.period_start.isnot(None))
                .order_by(Invoice.period_start.desc(), Invoice.created_at.desc())
                .first()
            )
            # A cancelled invoice leaves its period unbilled; reissuing keeps the schedule
            if last is not None and last.status == InvoiceStatus.cancelled:
                return last.period_start, False

        today = date.today()
        due = sub.next_billing_date or today
        if due > today:
            raise AlreadyBilledError(
                f"{sub.subscription_number} is already billed; next invoice is due on {due}"
            )
        if sub.expiry_date and due > sub.expiry_date:
            raise NotBillableError(f"{sub.subscription_number} expired on {sub.expiry_date}")
        return due, True

    def _lines_for(self, sub: Subscription):
        if sub.lines:
            return sub.lines
        delta = sub.variant.price_delta if sub.variant else 0
        return [
            _FakeLine(
                product_id=sub.plan.product_id,
                unit_price=Decimal(str(sub.plan.price)) + Decimal(str(delta)),
                quantity=sub.plan.min_quantity or 1,
                product=sub.plan.product,
                variant=sub.variant,
            )
        ]

    def generate_for_subscription(
        self, subscription_id, auto_confirm: bool = False, reissue: bool = True
    ) -> Invoice:
        # The lock makes simultaneous requests for one subscription take turns
        sub = (
            self.db.query(Subscription)
            .filter(Subscription.id == subscription_id)
            .populate_existing()
            .with_for_update()
            .first()
        )
        if not sub:
            raise ValueError("Subscription not found")
        if sub.status != SubscriptionStatus.active:
            raise NotBillableError(
                f"Only active subscriptions can be invoiced (this one is {sub.status.value})"
            )

        period_start, advances = self._next_period(sub, reissue)
        next_start = next_billing_date_for(
            sub.plan.billing_interval, period_start, anchor=sub.start_date
        )

        invoice = Invoice(
            invoice_number=generate_invoice_number(self.db),
            subscription_id=sub.id,
            customer_id=sub.customer_id,
            customer_name=sub.customer.full_name,
            customer_email=sub.customer.email,
            status=InvoiceStatus.draft,
            due_date=date.today() + timedelta(days=sub.payment_terms or 0),
            period_start=period_start,
            period_end=next_start - timedelta(days=1),
        )

        tax_calc = TaxCalculator(self.db)
        discount_engine = DiscountEngine(self.db)

        source = self._lines_for(sub)
        amounts = [
            (line.product_id, line.quantity or 1, Decimal(str(line.unit_price)) * (line.quantity or 1))
            for line in source
        ]
        discounts, used = discount_engine.price_lines(amounts, sub.customer_id, sub.id)

        subtotal = tax_total = discount_total = grand_total = Decimal("0")
        for line, (product_id, quantity, amount), discount in zip(source, amounts, discounts):
            taxable = amount - discount
            tax_amount = tax_calc.calculate(product_id, taxable, plan_id=sub.plan_id)
            description = getattr(line.product, "name", "Subscription charge")
            if line.variant:
                description = f"{description} ({line.variant.label})"

            invoice.lines.append(
                InvoiceLine(
                    product_id=product_id,
                    description=description,
                    quantity=quantity,
                    unit_price=Decimal(str(line.unit_price)),
                    tax_amount=tax_amount,
                    discount=discount,
                    line_total=taxable + tax_amount,
                )
            )
            subtotal += amount
            tax_total += tax_amount
            discount_total += discount
            grand_total += taxable + tax_amount

        invoice.subtotal = subtotal
        invoice.tax_total = tax_total
        invoice.discount_total = discount_total
        invoice.grand_total = grand_total

        self.db.add(invoice)
        self.db.flush()

        for discount, amount in used.items():
            discount_engine.mark_used(discount)
            self.db.add(
                DiscountRedemption(discount_id=discount.id, invoice_id=invoice.id, amount=amount)
            )

        if advances:
            sub.next_billing_date = next_start
            self.db.add(sub)

        if auto_confirm:
            self._mark_confirmed(invoice)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            if "uq_invoices_subscription_period" in str(exc):
                raise AlreadyBilledError(f"Period {period_start} is already billed")
            raise
        self.db.refresh(invoice)
        return invoice

    def _mark_confirmed(self, invoice: Invoice):
        now = datetime.now(timezone.utc)
        invoice.issued_at = now
        # Nothing to collect on a fully discounted invoice
        if Decimal(str(invoice.grand_total)) == 0:
            invoice.status = InvoiceStatus.paid
            invoice.paid_at = now
        else:
            invoice.status = InvoiceStatus.confirmed
        self.db.add(invoice)

    def _locked(self, invoice_id) -> Invoice:
        invoice = (
            self.db.query(Invoice)
            .filter(Invoice.id == invoice_id)
            .populate_existing()
            .with_for_update()
            .first()
        )
        if not invoice:
            raise ValueError("Invoice not found")
        return invoice

    def confirm(self, invoice_id) -> Invoice:
        invoice = self._locked(invoice_id)
        if invoice.status != InvoiceStatus.draft:
            raise NotBillableError("Only draft invoices can be confirmed")
        self._mark_confirmed(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def cancel(self, invoice_id) -> Invoice:
        invoice = self._locked(invoice_id)
        if invoice.status not in (InvoiceStatus.draft, InvoiceStatus.confirmed):
            raise NotBillableError("Only draft or confirmed invoices can be cancelled")
        if Decimal(str(invoice.amount_paid)) > 0:
            raise NotBillableError("This invoice has payments recorded against it")

        engine = DiscountEngine(self.db)
        redemptions = (
            self.db.query(DiscountRedemption)
            .filter(DiscountRedemption.invoice_id == invoice.id)
            .all()
        )
        for redemption in redemptions:
            engine.release(redemption.discount)
            self.db.delete(redemption)

        invoice.status = InvoiceStatus.cancelled
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice
