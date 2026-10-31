from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.payment import Payment
from app.models.invoice import Invoice, InvoiceStatus


class PaymentService:
    """
    Payment recording service.
    Auto-reconciles invoice to 'paid' when total payments >= grand_total.
    """

    def __init__(self, db: Session):
        self.db = db

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
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Invoice not found")
        if invoice.status == InvoiceStatus.cancelled:
            raise ValueError("Cannot record payment on a cancelled invoice")

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
        self.db.flush()  # get the payment into the session so invoice.payments is current

        # Recompute total paid including this new payment
        total_paid = sum(
            (Decimal(str(p.amount)) for p in invoice.payments),
            Decimal("0"),
        )

        if total_paid >= Decimal(str(invoice.grand_total)):
            invoice.status = InvoiceStatus.paid
            self.db.add(invoice)

        self.db.commit()
        self.db.refresh(payment)
        return payment

