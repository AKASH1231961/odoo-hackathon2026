import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_staff
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionHistoryOut,
    SubscriptionLineCreate,
    SubscriptionLineUpdate,
    SubscriptionOut,
    SubscriptionUpdate,
)
from app.services.subscription_service import SubscriptionService
from app.utils.pagination import Page, paged

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.post("", response_model=SubscriptionOut, status_code=201)
def create_subscription(
    payload: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    return SubscriptionService(db).create(payload, current_user.id)


@router.get("", response_model=List[SubscriptionOut])
def list_subscriptions(
    status: Optional[SubscriptionStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
    plan_id: Optional[uuid.UUID] = None,
    search: Optional[str] = Query(None, description="Matches number, customer name, email or company"),
    page: Page = Depends(paged()),
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    q = db.query(Subscription)
    if search:
        term = f"%{search}%"
        q = q.join(User, Subscription.customer_id == User.id).filter(
            or_(
                Subscription.subscription_number.ilike(term),
                User.full_name.ilike(term),
                User.email.ilike(term),
                User.company_name.ilike(term),
            )
        )
    if status:
        q = q.filter(Subscription.status == status)
    if customer_id:
        q = q.filter(Subscription.customer_id == customer_id)
    if plan_id:
        q = q.filter(Subscription.plan_id == plan_id)
    return page.apply(q, Subscription.created_at.desc())


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


@router.get("/{subscription_id}/history", response_model=List[SubscriptionHistoryOut])
def subscription_history(
    subscription_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    return get_subscription(subscription_id, db, _).status_history


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
    if sub.start_date and sub.expiry_date and sub.expiry_date < sub.start_date:
        raise HTTPException(400, "expiry_date cannot be before start_date")
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


# ── Lines ─────────────────────────────────────────────────────────────────────

@router.post("/{subscription_id}/lines", response_model=SubscriptionOut, status_code=201)
def add_line(
    subscription_id: uuid.UUID,
    payload: SubscriptionLineCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    return SubscriptionService(db).add_line(
        subscription_id, payload.product_id, payload.quantity, payload.unit_price, payload.variant_id
    )


@router.patch("/{subscription_id}/lines/{line_id}", response_model=SubscriptionOut)
def update_line(
    subscription_id: uuid.UUID,
    line_id: uuid.UUID,
    payload: SubscriptionLineUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    return SubscriptionService(db).update_line(subscription_id, line_id, payload.quantity)


@router.delete("/{subscription_id}/lines/{line_id}", response_model=SubscriptionOut)
def remove_line(
    subscription_id: uuid.UUID,
    line_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    return SubscriptionService(db).remove_line(subscription_id, line_id)


# ── State Machine Transitions ─────────────────────────────────────────────────

@router.post("/{subscription_id}/quotation", response_model=SubscriptionOut)
def send_to_quotation(subscription_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_staff)):
    return SubscriptionService(db).send_to_quotation(subscription_id, current_user.id)


@router.post("/{subscription_id}/confirm", response_model=SubscriptionOut)
def confirm(subscription_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_staff)):
    return SubscriptionService(db).confirm(subscription_id, current_user.id)


@router.post("/{subscription_id}/activate", response_model=SubscriptionOut)
def activate(subscription_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_staff)):
    return SubscriptionService(db).activate(subscription_id, current_user.id)


@router.post("/{subscription_id}/pause", response_model=SubscriptionOut)
def pause(subscription_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_staff)):
    return SubscriptionService(db).pause(subscription_id, current_user.id)


@router.post("/{subscription_id}/resume", response_model=SubscriptionOut)
def resume(subscription_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_staff)):
    return SubscriptionService(db).resume(subscription_id, current_user.id)


@router.post("/{subscription_id}/close", response_model=SubscriptionOut)
def close(subscription_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_staff)):
    return SubscriptionService(db).close(subscription_id, current_user.id)


@router.post("/{subscription_id}/renew", response_model=SubscriptionOut)
def renew(subscription_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_staff)):
    return SubscriptionService(db).renew(subscription_id, current_user.id)
