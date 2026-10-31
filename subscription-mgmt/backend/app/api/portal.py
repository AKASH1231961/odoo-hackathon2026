import uuid
from io import BytesIO
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_customer
from app.core.security import hash_password, validate_password_policy
from app.models.subscription import Subscription
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.subscription import SubscriptionOut
from app.schemas.invoice import InvoiceOut
from app.schemas.user import UserOut, ProfileUpdate
from app.utils.pdf import generate_invoice_pdf

router = APIRouter(prefix="/portal", tags=["Customer Portal"])


@router.get("/subscriptions", response_model=List[SubscriptionOut])
def my_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """Return only the current customer's subscriptions."""
    return (
        db.query(Subscription)
        .filter(Subscription.customer_id == current_user.id)
        .order_by(Subscription.created_at.desc())
        .all()
    )


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionOut)
def my_subscription_detail(
    subscription_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    # Return 404, not 403 — never reveal existence of other customers' resources
    sub = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.customer_id == current_user.id,
    ).first()
    if not sub:
        raise HTTPException(404, "Not found")
    return sub


@router.get("/invoices", response_model=List[InvoiceOut])
def my_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    return (
        db.query(Invoice)
        .filter(Invoice.customer_id == current_user.id)
        .order_by(Invoice.created_at.desc())
        .all()
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def my_invoice_detail(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.customer_id == current_user.id,
    ).first()
    if not invoice:
        raise HTTPException(404, "Not found")
    return invoice


@router.get("/invoices/{invoice_id}/pdf")
def my_invoice_pdf(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.customer_id == current_user.id,
    ).first()
    if not invoice:
        raise HTTPException(404, "Not found")
    pdf_bytes = generate_invoice_pdf(invoice)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice.invoice_number}.pdf"'},
    )


@router.get("/profile", response_model=UserOut)
def my_profile(current_user: User = Depends(require_customer)):
    return current_user


@router.patch("/profile", response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.password:
        if not validate_password_policy(payload.password):
            raise HTTPException(
                400,
                "Password must be at least 8 characters with uppercase, lowercase, and a special character",
            )
        current_user.password_hash = hash_password(payload.password)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

