from datetime import date
from sqlalchemy.orm import Session
from app.models.subscription import Subscription
from app.models.invoice import Invoice


def generate_subscription_number(db: Session) -> str:
    """Format: SUB-YYYYMM-XXXXX (e.g. SUB-202611-00042)"""
    today = date.today()
    prefix = f"SUB-{today.strftime('%Y%m')}-"
    count = (
        db.query(Subscription)
        .filter(Subscription.subscription_number.like(f"{prefix}%"))
        .count()
    )
    return f"{prefix}{count + 1:05d}"


def generate_invoice_number(db: Session) -> str:
    """Format: INV-YYYYMM-XXXXX (e.g. INV-202611-00105)"""
    today = date.today()
    prefix = f"INV-{today.strftime('%Y%m')}-"
    count = (
        db.query(Invoice)
        .filter(Invoice.invoice_number.like(f"{prefix}%"))
        .count()
    )
    return f"{prefix}{count + 1:05d}"

