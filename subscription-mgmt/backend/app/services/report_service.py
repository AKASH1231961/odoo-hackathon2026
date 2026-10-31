from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment


class ReportService:
    """
    Finance reporting service.
    All aggregations performed at the DB level — never Python loops.
    Designed for sub-2s response times on thousands of records.
    """

    def __init__(self, db: Session):
        self.db = db

    def summary(self) -> dict:
        today = date.today()
        month_start = today.replace(day=1)

        active_count = (
            self.db.query(func.count(Subscription.id))
            .filter(Subscription.status == SubscriptionStatus.active)
            .scalar()
        )

        revenue_this_month = (
            self.db.query(func.coalesce(func.sum(Invoice.grand_total), 0))
            .filter(
                Invoice.status == InvoiceStatus.paid,
                Invoice.issued_at >= month_start,
            )
            .scalar()
        )

        outstanding = (
            self.db.query(func.coalesce(func.sum(Invoice.grand_total), 0))
            .filter(Invoice.status == InvoiceStatus.confirmed)
            .scalar()
        )

        overdue_count = (
            self.db.query(func.count(Invoice.id))
            .filter(
                Invoice.status == InvoiceStatus.confirmed,
                Invoice.due_date < today,
            )
            .scalar()
        )

        return {
            "active_subscription_count": int(active_count or 0),
            "total_revenue_this_month": float(revenue_this_month or 0),
            "outstanding_amount": float(outstanding or 0),
            "overdue_invoice_count": int(overdue_count or 0),
        }

    def revenue_by_month(self, date_from: date, date_to: date) -> list:
        """DB-aggregated monthly revenue — uses DATE_TRUNC for Postgres efficiency."""
        rows = (
            self.db.query(
                func.date_trunc("month", Invoice.issued_at).label("month"),
                func.sum(Invoice.grand_total).label("total"),
            )
            .filter(
                Invoice.status == InvoiceStatus.paid,
                Invoice.issued_at >= date_from,
                Invoice.issued_at <= date_to,
            )
            .group_by("month")
            .order_by("month")
            .all()
        )
        return [
            {"month": r.month.strftime("%Y-%m"), "revenue": float(r.total)}
            for r in rows
        ]

    def overdue_invoices(self) -> list:
        today = date.today()
        invoices = (
            self.db.query(Invoice)
            .filter(
                Invoice.status == InvoiceStatus.confirmed,
                Invoice.due_date < today,
            )
            .order_by((today - Invoice.due_date).desc())
            .all()
        )
        return [
            {
                "invoice_id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "customer_id": str(inv.customer_id),
                "grand_total": float(inv.grand_total),
                "due_date": str(inv.due_date),
                "days_overdue": (today - inv.due_date).days,
            }
            for inv in invoices
        ]

