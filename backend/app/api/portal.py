import uuid
from decimal import Decimal
from io import BytesIO
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_customer
from app.core.security import hash_password, validate_password_policy
from app.models.product import Product
from app.models.subscription import Subscription
from app.models.invoice import Invoice, InvoiceStatus
from app.models.user import User
from app.schemas.product import ProductVariantOut
from app.schemas.subscription import SubscriptionLineCreate, SubscriptionOut
from app.schemas.invoice import InvoiceOut
from app.schemas.user import UserOut, ProfileUpdate
from app.services.subscription_service import SubscriptionService
from app.utils.pdf import generate_invoice_pdf

router = APIRouter(prefix="/portal", tags=["Customer Portal"])


class AddOnOut(BaseModel):
    id: uuid.UUID
    name: str
    sales_price: Decimal
    notes: Optional[str] = None
    variants: List[ProductVariantOut] = []

    model_config = {"from_attributes": True}


def _is_addon(product: Product) -> bool:
    return "add" in (product.type or "").lower()


def _own_subscription(db: Session, subscription_id, customer: User) -> Subscription:
    # Return 404, not 403 — never reveal existence of other customers' resources
    sub = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.customer_id == customer.id,
    ).first()
    if not sub:
        raise HTTPException(404, "Not found")
    return sub


def _visible_invoices(db: Session, customer: User):
    """Drafts are internal until the team confirms them."""
    return db.query(Invoice).filter(
        Invoice.customer_id == customer.id,
        Invoice.status != InvoiceStatus.draft,
    )


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
    return _own_subscription(db, subscription_id, current_user)


@router.post("/subscriptions/{subscription_id}/pause", response_model=SubscriptionOut)
def pause_my_subscription(
    subscription_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    sub = _own_subscription(db, subscription_id, current_user)
    return SubscriptionService(db).pause(sub.id, current_user.id)


@router.post("/subscriptions/{subscription_id}/resume", response_model=SubscriptionOut)
def resume_my_subscription(
    subscription_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    sub = _own_subscription(db, subscription_id, current_user)
    return SubscriptionService(db).resume(sub.id, current_user.id)


@router.post("/subscriptions/{subscription_id}/close", response_model=SubscriptionOut)
def close_my_subscription(
    subscription_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    sub = _own_subscription(db, subscription_id, current_user)
    return SubscriptionService(db).close(sub.id, current_user.id)


@router.post("/subscriptions/{subscription_id}/renew", response_model=SubscriptionOut)
def renew_my_subscription(
    subscription_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    sub = _own_subscription(db, subscription_id, current_user)
    return SubscriptionService(db).renew(sub.id, current_user.id)


@router.get("/addons", response_model=List[AddOnOut])
def available_addons(
    db: Session = Depends(get_db),
    _: User = Depends(require_customer),
):
    products = db.query(Product).filter(Product.is_active.is_(True)).order_by(Product.name).all()
    return [p for p in products if _is_addon(p)]


@router.post("/subscriptions/{subscription_id}/addons", response_model=SubscriptionOut, status_code=201)
def switch_on_addon(
    subscription_id: uuid.UUID,
    payload: SubscriptionLineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """Add an add-on at catalogue price; it appears on the next invoice."""
    sub = _own_subscription(db, subscription_id, current_user)
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product or not _is_addon(product):
        raise HTTPException(400, "That product is not an add-on")
    return SubscriptionService(db).add_line(
        sub.id, payload.product_id, payload.quantity, variant_id=payload.variant_id
    )


@router.delete("/subscriptions/{subscription_id}/addons/{line_id}", response_model=SubscriptionOut)
def switch_off_addon(
    subscription_id: uuid.UUID,
    line_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    sub = _own_subscription(db, subscription_id, current_user)
    return SubscriptionService(db).remove_line(sub.id, line_id)


@router.get("/invoices", response_model=List[InvoiceOut])
def my_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    return _visible_invoices(db, current_user).order_by(Invoice.created_at.desc()).all()


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def my_invoice_detail(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    invoice = _visible_invoices(db, current_user).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(404, "Not found")
    return invoice


@router.get("/invoices/{invoice_id}/pdf")
def my_invoice_pdf(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    invoice = _visible_invoices(db, current_user).filter(Invoice.id == invoice_id).first()
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
    for field in ("full_name", "company_name", "phone", "address"):
        value = getattr(payload, field)
        if value is not None:
            setattr(current_user, field, value)
    if payload.password:
        if not validate_password_policy(payload.password):
            raise HTTPException(
                400,
                "Password must be more than 8 characters with uppercase, lowercase, and a special character",
            )
        current_user.password_hash = hash_password(payload.password)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

