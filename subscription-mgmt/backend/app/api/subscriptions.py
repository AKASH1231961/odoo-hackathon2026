import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_staff
from app.models.subscription import Subscription, SubscriptionLine, SubscriptionStatus
from app.models.user import User
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate, SubscriptionOut
from app.services.numbering import generate_subscription_number
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.post("", response_model=SubscriptionOut, status_code=201)
def create_subscription(
    payload: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    sub = Subscription(
        subscription_number=generate_subscription_number(db),
        customer_id=payload.customer_id,
        plan_id=payload.plan_id,
        variant_id=payload.variant_id,
        template_id=payload.template_id,
        start_date=payload.start_date,
        expiry_date=payload.expiry_date,
        payment_terms=payload.payment_terms,
        status=SubscriptionStatus.draft,
        created_by=current_user.id,
    )
    db.add(sub)
    db.flush()  # get sub.id before adding lines

    for line in payload.lines:
        db.add(SubscriptionLine(
            subscription_id=sub.id,
            product_id=line.product_id,
            quantity=line.quantity,
            unit_price=line.unit_price,
            line_total=line.unit_price * line.quantity,
        ))

    db.commit()
    db.refresh(sub)
    return sub


@router.get("", response_model=List[SubscriptionOut])
def list_subscriptions(
    status: Optional[SubscriptionStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
    plan_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 25,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    q = db.query(Subscription)
    if status:
        q = q.filter(Subscription.status == status)
    if customer_id:
        q = q.filter(Subscription.customer_id == customer_id)
    if plan_id:
        q = q.filter(Subscription.plan_id == plan_id)
    return q.order_by(Subscription.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{subscription_id}", response_model=SubscriptionOut)
def get_subscription(
    subscription_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(404, "Subscription not found")
    return sub


@router.patch("/{subscription_id}", response_model=SubscriptionOut)
def update_subscription(
    subscription_id: uuid.UUID,
    payload: SubscriptionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(404, "Subscription not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(sub, k, v)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


# ── State Machine Transitions ─────────────────────────────────────────────────

@router.post("/{subscription_id}/quotation", response_model=SubscriptionOut)
def send_to_quotation(subscription_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    return SubscriptionService(db).send_to_quotation(subscription_id)


@router.post("/{subscription_id}/confirm", response_model=SubscriptionOut)
def confirm(subscription_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    return SubscriptionService(db).confirm(subscription_id)


@router.post("/{subscription_id}/activate", response_model=SubscriptionOut)
def activate(subscription_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    return SubscriptionService(db).activate(subscription_id)


@router.post("/{subscription_id}/pause", response_model=SubscriptionOut)
def pause(subscription_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    return SubscriptionService(db).pause(subscription_id)


@router.post("/{subscription_id}/resume", response_model=SubscriptionOut)
def resume(subscription_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    return SubscriptionService(db).resume(subscription_id)


@router.post("/{subscription_id}/close", response_model=SubscriptionOut)
def close(subscription_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    return SubscriptionService(db).close(subscription_id)


@router.post("/{subscription_id}/renew", response_model=SubscriptionOut)
def renew(subscription_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    return SubscriptionService(db).renew(subscription_id)

