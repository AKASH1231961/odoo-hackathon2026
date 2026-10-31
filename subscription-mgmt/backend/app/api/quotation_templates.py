import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_staff
from app.models.quotation_template import QuotationTemplate
from app.models.user import User
from app.schemas.quotation_template import QuotationTemplateCreate, QuotationTemplateUpdate, QuotationTemplateOut

router = APIRouter(prefix="/quotation-templates", tags=["Quotation Templates"])


@router.post("", response_model=QuotationTemplateOut, status_code=201)
def create_template(
    payload: QuotationTemplateCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    tpl = QuotationTemplate(**payload.model_dump())
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.get("", response_model=List[QuotationTemplateOut])
def list_templates(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    return db.query(QuotationTemplate).order_by(QuotationTemplate.created_at.desc()).all()


@router.get("/{template_id}", response_model=QuotationTemplateOut)
def get_template(template_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    tpl = db.query(QuotationTemplate).filter(QuotationTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(404, "Template not found")
    return tpl


@router.patch("/{template_id}", response_model=QuotationTemplateOut)
def update_template(
    template_id: uuid.UUID,
    payload: QuotationTemplateUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    tpl = db.query(QuotationTemplate).filter(QuotationTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(404, "Template not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(tpl, k, v)
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.delete("/{template_id}")
def delete_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    tpl = db.query(QuotationTemplate).filter(QuotationTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(404, "Template not found")
    db.delete(tpl)
    db.commit()
    return {"message": "Deleted"}

