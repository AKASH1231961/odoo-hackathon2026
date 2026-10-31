import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_staff
from app.models.product import Product, ProductVariant
from app.models.user import User
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductOut,
    ProductVariantCreate, ProductVariantOut,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", response_model=ProductOut, status_code=201)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=List[ProductOut])
def list_products(is_active: Optional[bool] = None, db: Session = Depends(get_db)):
    q = db.query(Product)
    if is_active is not None:
        q = q.filter(Product.is_active == is_active)
    return q.order_by(Product.created_at.desc()).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(product, k, v)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=200)
def deactivate_product(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Soft delete — sets is_active=False."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    product.is_active = False
    db.add(product)
    db.commit()
    return {"message": "Product deactivated"}


# ── Variants ──────────────────────────────────────────────────────────────────

@router.post("/{product_id}/variants", response_model=ProductVariantOut, status_code=201)
def add_variant(
    product_id: uuid.UUID,
    payload: ProductVariantCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    variant = ProductVariant(product_id=product_id, **payload.model_dump())
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.get("/{product_id}/variants", response_model=List[ProductVariantOut])
def list_variants(product_id: uuid.UUID, db: Session = Depends(get_db)):
    return (
        db.query(ProductVariant)
        .filter(ProductVariant.product_id == product_id)
        .all()
    )


@router.patch("/{product_id}/variants/{variant_id}", response_model=ProductVariantOut)
def update_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    payload: ProductVariantCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    variant = (
        db.query(ProductVariant)
        .filter(ProductVariant.id == variant_id, ProductVariant.product_id == product_id)
        .first()
    )
    if not variant:
        raise HTTPException(404, "Variant not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(variant, k, v)
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.delete("/{product_id}/variants/{variant_id}")
def deactivate_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    variant = (
        db.query(ProductVariant)
        .filter(ProductVariant.id == variant_id, ProductVariant.product_id == product_id)
        .first()
    )
    if not variant:
        raise HTTPException(404, "Variant not found")
    variant.is_active = False
    db.add(variant)
    db.commit()
    return {"message": "Variant deactivated"}

