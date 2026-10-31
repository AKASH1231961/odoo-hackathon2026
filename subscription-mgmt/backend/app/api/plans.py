import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_staff
from app.models.plan import Plan, BillingInterval
from app.models.user import User
from app.schemas.plan import PlanCreate, PlanUpdate, PlanOut

router = APIRouter(prefix="/plans", tags=["Plans"])


@router.post("", response_model=PlanOut, status_code=201)
def create_plan(
    payload: PlanCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    plan = Plan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("", response_model=List[PlanOut])
def list_plans(
    product_id: Optional[uuid.UUID] = None,
    billing_interval: Optional[BillingInterval] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Plan)
    if product_id:
        q = q.filter(Plan.product_id == product_id)
    if billing_interval:
        q = q.filter(Plan.billing_interval == billing_interval)
    if is_active is not None:
        q = q.filter(Plan.is_active == is_active)
    return q.order_by(Plan.created_at.desc()).all()


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: uuid.UUID, db: Session = Depends(get_db)):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    return plan


@router.patch("/{plan_id}", response_model=PlanOut)
def update_plan(
    plan_id: uuid.UUID,
    payload: PlanUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(plan, k, v)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/{plan_id}/close", response_model=PlanOut)
def close_plan(
    plan_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Manually close (deactivate) a plan early."""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    plan.is_active = False
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

