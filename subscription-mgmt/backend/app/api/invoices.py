import uuid
from datetime import datetime, date
from io import BytesIO
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_staff
from app.models.invoice import Invoice, InvoiceStatus
from app.models.user import User
from app.schemas.invoice import InvoiceOut
from app.utils.pdf import generate_invoice_pdf
from app.utils.email import send_email
from app.services.invoicing_service import InvoicingService, AlreadyBilledError

router = APIRouter(tags=["Invoices"])


@router.get("/invoices", response_model=List[InvoiceOut])
def list_invoices(
    status: Optional[InvoiceStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
    overdue: Optional[bool] = None,
    skip: int = 0,
    limit: int = 25,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    q = db.query(Invoice)
    if status:
        q = q.filter(Invoice.status == status)
    if customer_id:
        q = q.filter(Invoice.customer_id == customer_id)
    if overdue:
        q = q.filter(Invoice.due_date < date.today(), Invoice.status != InvoiceStatus.paid)
    return q.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    return invoice


@router.post("/invoices/{invoice_id}/confirm", response_model=InvoiceOut)
def confirm_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    if invoice.status != InvoiceStatus.draft:
        raise HTTPException(400, "Only draft invoices can be confirmed")
    invoice.status = InvoiceStatus.confirmed
    invoice.issued_at = datetime.utcnow()
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/invoices/{invoice_id}/cancel", response_model=InvoiceOut)
def cancel_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    if invoice.status not in (InvoiceStatus.draft, InvoiceStatus.confirmed):
        raise HTTPException(400, "Only draft or confirmed invoices can be cancelled")
    invoice.status = InvoiceStatus.cancelled
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/invoices/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
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
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    pdf_bytes = generate_invoice_pdf(invoice)
    send_email(
        to=invoice.customer.email,
        subject=f"Brightloop — Invoice {invoice.invoice_number}",
        body=(
            f"Dear {invoice.customer.full_name or invoice.customer.email},\n\n"
            f"Please find attached your invoice {invoice.invoice_number}.\n"
            f"Amount due: {invoice.grand_total}\n"
            f"Due date: {invoice.due_date}\n\n"
            "Thank you for your business.\nBrightloop Software"
        ),
        attachment=pdf_bytes,
        attachment_name=f"{invoice.invoice_number}.pdf",
    )
    return {"message": "Invoice sent to customer"}


@router.post("/invoices/generate/{subscription_id}", response_model=InvoiceOut, status_code=201)
def generate_invoice(
    subscription_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Manually trigger invoice generation for a subscription."""
    try:
        return InvoicingService(db).generate_for_subscription(subscription_id)
    except AlreadyBilledError as e:
        raise HTTPException(400, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))

