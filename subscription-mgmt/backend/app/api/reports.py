import json
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import redis
from app.core.database import get_db
from app.core.deps import require_staff
from app.core.config import settings
from app.models.user import User
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])

try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None

CACHE_TTL = 60  # seconds


def _cache_get(key: str):
    if redis_client is None:
        return None
    try:
        val = redis_client.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


def _cache_set(key: str, data):
    if redis_client is None:
        return
    try:
        redis_client.setex(key, CACHE_TTL, json.dumps(data))
    except Exception:
        pass


@router.get("/summary")
def summary(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    """Finance dashboard summary — cached in Redis for 60s."""
    cached = _cache_get("reports:summary")
    if cached:
        return cached
    data = ReportService(db).summary()
    _cache_set("reports:summary", data)
    return data


@router.get("/revenue")
def revenue(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Monthly revenue breakdown — DB-aggregated, suitable for charting."""
    return ReportService(db).revenue_by_month(from_date, to_date)


@router.get("/overdue")
def overdue(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    """Overdue confirmed invoices sorted by days_overdue DESC."""
    return ReportService(db).overdue_invoices()

