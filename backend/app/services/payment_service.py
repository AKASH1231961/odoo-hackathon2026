from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.payment import Payment
from app.models.invoice import Invoice, InvoiceStatus


class PaymentService:
    """
    Payment recording service.
    Payments go against confirmed invoices, up to the balance due. The invoice's paid
    amount and status are recomputed from its payments on every change.
    """

    def __init__(self, db: Session):
        self.db = db

    def _locked_invoice(self, invoice_id) -> Invoice:
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

    def _check_date(self, payment_date: date):
        if payment_date > date.today():
            raise ValueError("Payment date cannot be in the future")

    def _reconcile(self, invoice: Invoice):
        self.db.flush()
        self.db.expire(invoice, ["payments"])
        paid = sum((Decimal(str(p.amount)) for p in invoice.payments), Decimal("0"))
        invoice.amount_paid = paid
        if paid >= Decimal(str(invoice.grand_total)):
            if invoice.status != InvoiceStatus.paid:
                invoice.paid_at = datetime.now(timezone.utc)
            invoice.status = InvoiceStatus.paid
        else:
            invoice.status = InvoiceStatus.confirmed
            invoice.paid_at = None
        self.db.add(invoice)

    def record(
        self,
        invoice_id,
        amount: Decimal,
        method,
        payment_date,
        reference: str,
        note: str,
        recorded_by,
    ) -> Payment:
        invoice = self._locked_invoice(invoice_id)
        if invoice.status == InvoiceStatus.cancelled:
            raise ValueError("Cannot record payment on a cancelled invoice")
        if invoice.status == InvoiceStatus.draft:
            raise ValueError("Confirm the invoice before recording a payment")
        if invoice.status == InvoiceStatus.paid:
            raise ValueError("This invoice is already fully paid")
        self._check_date(payment_date)

        balance = invoice.balance_due
        if amount > balance:
            raise ValueError(f"Payment of {amount} is more than the balance due of {balance}")

        payment = Payment(
            invoice_id=invoice_id,
            amount=amount,
            method=method,
            payment_date=payment_date,
            reference=reference,
            note=note,
            recorded_by=recorded_by,
        )
        self.db.add(payment)
        self._reconcile(invoice)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def update(self, payment_id, values: dict) -> Payment:
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise LookupError("Payment not found")
        invoice = self._locked_invoice(payment.invoice_id)
        if invoice.status == InvoiceStatus.cancelled:
            raise ValueError("Cannot change a payment on a cancelled invoice")

        if "payment_date" in values:
            self._check_date(values["payment_date"])
        if "amount" in values:
            others = Decimal(str(invoice.amount_paid)) - Decimal(str(payment.amount))
            if others + values["amount"] > Decimal(str(invoice.grand_total)):
                raise ValueError("Payments would be more than the invoice total")

        for key, value in values.items():
            setattr(payment, key, value)
        self.db.add(payment)
        self._reconcile(invoice)
        self.db.commit()
        self.db.refresh(payment)
        return payment
