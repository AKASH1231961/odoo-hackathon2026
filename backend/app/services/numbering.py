from datetime import date
from sqlalchemy import text
from sqlalchemy.orm import Session


def _next_number(db: Session, prefix: str) -> str:
    """
    Atomic per-prefix counter. The row stays locked until the caller commits, so two
    transactions can never receive the same number, and a rollback leaves no gap.
    """
    value = db.execute(
        text(
            "INSERT INTO number_sequences (prefix, last_value) VALUES (:prefix, 1) "
            "ON CONFLICT (prefix) DO UPDATE SET last_value = number_sequences.last_value + 1 "
            "RETURNING last_value"
        ),
        {"prefix": prefix},
    ).scalar_one()
    return f"{prefix}{value:05d}"


def generate_subscription_number(db: Session) -> str:
    """Format: SUB-YYYYMM-XXXXX (e.g. SUB-202611-00042)"""
    return _next_number(db, f"SUB-{date.today().strftime('%Y%m')}-")


def generate_invoice_number(db: Session) -> str:
    """Format: INV-YYYYMM-XXXXX (e.g. INV-202611-00105)"""
    return _next_number(db, f"INV-{date.today().strftime('%Y%m')}-")
