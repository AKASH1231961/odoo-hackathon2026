import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_admin
from app.models.discount import Discount
from app.models.user import User
from app.schemas.discount import DiscountCreate, DiscountUpdate, DiscountOut

router = APIRouter(prefix="/discounts", tags=["Discounts"])


@router.post("", response_model=DiscountOut, status_code=201)
def create_discount(
    payload: DiscountCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    discount = Discount(**payload.model_dump())
    db.add(discount)
    db.commit()
    db.refresh(discount)
    return discount


@router.get("", response_model=List[DiscountOut])
def list_discounts(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.query(Discount).order_by(Discount.created_at.desc()).all()


@router.get("/{discount_id}", response_model=DiscountOut)
def get_discount(discount_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    discount = db.query(Discount).filter(Discount.id == discount_id).first()
    if not discount:
        raise HTTPException(404, "Discount not found")
    return discount


@router.patch("/{discount_id}", response_model=DiscountOut)
def update_discount(
    discount_id: uuid.UUID,
    payload: DiscountUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    discount = db.query(Discount).filter(Discount.id == discount_id).first()
    if not discount:
        raise HTTPException(404, "Discount not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(discount, k, v)
    db.add(discount)
    db.commit()
    db.refresh(discount)
    return discount


@router.delete("/{discount_id}")
def deactivate_discount(
    discount_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    discount = db.query(Discount).filter(Discount.id == discount_id).first()
    if not discount:
        raise HTTPException(404, "Discount not found")
    discount.is_active = False
    db.add(discount)
    db.commit()
    return {"message": "Discount deactivated"}

