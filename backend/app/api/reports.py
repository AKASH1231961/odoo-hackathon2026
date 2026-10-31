import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_staff
from app.models.user import User
from app.services.report_service import ReportService
from app.utils.pagination import Page, paged

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/summary")
def summary(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    plan_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Finance dashboard summary; defaults to this month."""
    return ReportService(db).summary(from_date, to_date, plan_id)


@router.get("/revenue")
def revenue(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    plan_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Monthly money received — DB-aggregated, suitable for charting."""
    return ReportService(db).revenue_by_month(from_date, to_date, plan_id)


@router.get("/payments")
def payments(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    plan_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Money received per payment method."""
    return ReportService(db).payments_by_method(from_date, to_date, plan_id)


@router.get("/by-plan")
def by_plan(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Subscriptions per plan, and money received in the period."""
    return ReportService(db).by_plan(from_date, to_date)


@router.get("/overdue")
def overdue(
    page: Page = Depends(paged(100)),
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Overdue invoices, longest overdue first."""
    return ReportService(db).overdue_invoices(page)


@router.get("/renewals")
def renewals(
    days: int = Query(30, ge=0, le=366),
    page: Page = Depends(paged(100)),
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Active subscriptions ending within the given number of days."""
    return ReportService(db).upcoming_renewals(page, days)
