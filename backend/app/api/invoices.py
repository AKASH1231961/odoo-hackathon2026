import uuid
from datetime import date, datetime, timezone
from io import BytesIO
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_admin, require_staff
from app.models.invoice import Invoice, InvoiceStatus
from app.models.user import User
from app.schemas.invoice import InvoiceOut
from app.utils.pdf import generate_invoice_pdf
from app.utils.email import send_email
from app.utils.pagination import Page, paged
from app.services.invoicing_service import AlreadyBilledError, InvoicingService, NotBillableError

router = APIRouter(tags=["Invoices"])


@router.get("/invoices", response_model=List[InvoiceOut])
def list_invoices(
    status: Optional[InvoiceStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
    subscription_id: Optional[uuid.UUID] = None,
    overdue: Optional[bool] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = Query(None, description="Matches invoice number, customer name, email or company"),
    page: Page = Depends(paged()),
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    q = db.query(Invoice)
    if search:
        term = f"%{search}%"
        q = q.join(User, Invoice.customer_id == User.id).filter(
            or_(
                Invoice.invoice_number.ilike(term),
                Invoice.customer_name.ilike(term),
                User.email.ilike(term),
                User.company_name.ilike(term),
            )
        )
    if status:
        q = q.filter(Invoice.status == status)
    if customer_id:
        q = q.filter(Invoice.customer_id == customer_id)
    if subscription_id:
        q = q.filter(Invoice.subscription_id == subscription_id)
    if overdue:
        q = q.filter(Invoice.due_date < date.today(), Invoice.status == InvoiceStatus.confirmed)
    if date_from:
        q = q.filter(Invoice.created_at >= date_from)
    if date_to:
        q = q.filter(Invoice.created_at < date.fromordinal(date_to.toordinal() + 1))
    return page.apply(q, Invoice.created_at.desc())


def _get_invoice(db: Session, invoice_id: uuid.UUID) -> Invoice:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    return invoice


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    return _get_invoice(db, invoice_id)


@router.post("/invoices/{invoice_id}/confirm", response_model=InvoiceOut)
def confirm_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    try:
        return InvoicingService(db).confirm(invoice_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except NotBillableError as e:
        raise HTTPException(400, str(e))


@router.post("/invoices/{invoice_id}/cancel", response_model=InvoiceOut)
def cancel_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    try:
        return InvoicingService(db).cancel(invoice_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except NotBillableError as e:
        raise HTTPException(400, str(e))


@router.get("/invoices/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    invoice = _get_invoice(db, invoice_id)
    pdf_bytes = generate_invoice_pdf(invoice)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice.invoice_number}.pdf"'},
    )


@router.post("/invoices/{invoice_id}/send")
def send_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Email the invoice PDF to the customer."""
    invoice = _get_invoice(db, invoice_id)
    if invoice.status not in (InvoiceStatus.confirmed, InvoiceStatus.paid):
        raise HTTPException(400, "Only confirmed or paid invoices can be sent")
    pdf_bytes = generate_invoice_pdf(invoice)
    sent = send_email(
        to=invoice.customer_email or invoice.customer.email,
        subject=f"Brightloop — Invoice {invoice.invoice_number}",
        body=(
            f"Dear {invoice.customer_name or invoice.customer.email},\n\n"
            f"Please find attached your invoice {invoice.invoice_number}.\n"
            f"Amount due: {invoice.balance_due}\n"
            f"Due date: {invoice.due_date}\n\n"
            "Thank you for your business.\nBrightloop Software"
        ),
        attachment=pdf_bytes,
        attachment_name=f"{invoice.invoice_number}.pdf",
    )
    if not sent:
        raise HTTPException(502, "The email could not be sent. Check the mail server settings.")
    invoice.sent_at = datetime.now(timezone.utc)
    db.add(invoice)
    db.commit()
    return {"message": "Invoice sent to customer"}


@router.post("/invoices/generate/{subscription_id}", response_model=InvoiceOut, status_code=201)
def generate_invoice(
    subscription_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Bill a subscription that is due now, or reissue a cancelled invoice."""
    try:
        return InvoicingService(db).generate_for_subscription(subscription_id)
    except (AlreadyBilledError, NotBillableError) as e:
        raise HTTPException(400, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/invoices/run-billing", status_code=202)
def run_billing_now(_: User = Depends(require_admin)):
    """Queue the billing cycle now instead of waiting for tonight's run."""
    from app.tasks.billing_tasks import run_billing_cycle

    return {"task_id": run_billing_cycle.delay().id}
