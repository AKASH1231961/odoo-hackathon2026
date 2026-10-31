import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_admin
from app.models.tax import TaxRule
from app.models.user import User
from app.schemas.tax import TaxRuleCreate, TaxRuleUpdate, TaxRuleOut

router = APIRouter(prefix="/tax-rules", tags=["Tax Rules"])


@router.post("", response_model=TaxRuleOut, status_code=201)
def create_tax_rule(
    payload: TaxRuleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    rule = TaxRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("", response_model=List[TaxRuleOut])
def list_tax_rules(db: Session = Depends(get_db)):
    return db.query(TaxRule).filter(TaxRule.is_active.is_(True)).all()


@router.get("/{rule_id}", response_model=TaxRuleOut)
def get_tax_rule(rule_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rule = db.query(TaxRule).filter(TaxRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Tax rule not found")
    return rule


@router.patch("/{rule_id}", response_model=TaxRuleOut)
def update_tax_rule(
    rule_id: uuid.UUID,
    payload: TaxRuleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    rule = db.query(TaxRule).filter(TaxRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Tax rule not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(rule, k, v)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}")
def deactivate_tax_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Soft delete — sets is_active=False."""
    rule = db.query(TaxRule).filter(TaxRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Tax rule not found")
    rule.is_active = False
    db.add(rule)
    db.commit()
    return {"message": "Tax rule deactivated"}

