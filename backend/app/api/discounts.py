import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_admin
from app.models.discount import Discount, DiscountScope
from app.models.product import Product
from app.models.user import User
from app.schemas.discount import DiscountCreate, DiscountUpdate, DiscountOut

router = APIRouter(prefix="/discounts", tags=["Discounts"])


def _resolve_products(db: Session, product_ids: List[uuid.UUID]):
    unique_ids = set(product_ids)
    products = db.query(Product).filter(Product.id.in_(unique_ids)).all() if unique_ids else []
    if len(products) != len(unique_ids):
        raise HTTPException(404, "One or more products were not found")
    return products


@router.post("", response_model=DiscountOut, status_code=201)
def create_discount(
    payload: DiscountCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    values = payload.model_dump(exclude={"product_ids"})
    product_ids = payload.product_ids
    if payload.scope == DiscountScope.product and not (payload.product_id or product_ids):
        raise HTTPException(400, "Product-scoped discounts require at least one product")
    discount = Discount(**values)
    discount.products = _resolve_products(db, product_ids)
    if payload.product_id:
        _resolve_products(db, [payload.product_id])
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
    values = payload.model_dump(exclude_unset=True, exclude={"product_ids"})
    for k, v in values.items():
        setattr(discount, k, v)
    if payload.product_ids is not None:
        discount.products = _resolve_products(db, payload.product_ids)
    if discount.scope == DiscountScope.product and not (discount.product_id or discount.products):
        raise HTTPException(400, "Product-scoped discounts require at least one product")
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
