import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_staff
from app.models.payment import Payment, PaymentMethod
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentUpdate, PaymentOut
from app.services.payment_service import PaymentService
from app.utils.pagination import Page, paged

router = APIRouter(tags=["Payments"])


@router.post("/payments", response_model=PaymentOut, status_code=201)
def record_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    service = PaymentService(db)
    try:
        return service.record(
            invoice_id=payload.invoice_id,
            amount=payload.amount,
            method=payload.method,
            payment_date=payload.payment_date,
            reference=payload.reference,
            note=payload.note,
            recorded_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/payments", response_model=List[PaymentOut])
def list_payments(
    invoice_id: Optional[uuid.UUID] = None,
    method: Optional[PaymentMethod] = None,
    page: Page = Depends(paged()),
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    q = db.query(Payment)
    if invoice_id:
        q = q.filter(Payment.invoice_id == invoice_id)
    if method:
        q = q.filter(Payment.method == method)
    return page.apply(q, Payment.created_at.desc())


@router.get("/invoices/{invoice_id}/payments", response_model=List[PaymentOut])
def get_invoice_payments(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    return db.query(Payment).filter(Payment.invoice_id == invoice_id).all()


@router.patch("/payments/{payment_id}", response_model=PaymentOut)
def update_payment(
    payment_id: uuid.UUID,
    payload: PaymentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    try:
        return PaymentService(db).update(payment_id, payload.model_dump(exclude_unset=True))
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
