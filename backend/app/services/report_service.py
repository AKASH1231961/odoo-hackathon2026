from datetime import date, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.subscription import Subscription, SubscriptionLine, SubscriptionStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment
from app.models.plan import BillingInterval, Plan

# Billing periods in a month, to compare plans that bill at different rates
PERIODS_PER_MONTH = {
    BillingInterval.daily: 365 / 12,
    BillingInterval.weekly: 52 / 12,
    BillingInterval.monthly: 1,
    BillingInterval.yearly: 1 / 12,
}


class ReportService:
    """
    Finance reporting service.
    All aggregations performed at the DB level — never Python loops.
    Revenue means money received, dated by payment; outstanding is what is still unpaid.
    """

    def __init__(self, db: Session):
        self.db = db

    def _for_plan(self, query, plan_id):
        if plan_id:
            query = query.join(Subscription, Invoice.subscription_id == Subscription.id).filter(
                Subscription.plan_id == plan_id
            )
        return query

    def _payments(self, columns, date_from, date_to, plan_id=None):
        query = self.db.query(*columns).filter(
            Payment.payment_date >= date_from,
            Payment.payment_date <= date_to,
        )
        if plan_id:
            query = self._for_plan(query.join(Invoice, Payment.invoice_id == Invoice.id), plan_id)
        return query

    def _overdue_filter(self, today, date_from=None, date_to=None):
        filters = [Invoice.status == InvoiceStatus.confirmed, Invoice.due_date < today]
        if date_from:
            filters.append(Invoice.due_date >= date_from)
        if date_to:
            filters.append(Invoice.due_date <= date_to)
        return filters

    def _mrr_by_plan(self) -> dict:
        """Monthly value of active subscriptions, before tax and invoice-time discounts."""
        rows = (
            self.db.query(
                Plan.id,
                Plan.billing_interval,
                func.sum(SubscriptionLine.line_total - SubscriptionLine.tax_amount),
            )
            .join(Subscription, Subscription.plan_id == Plan.id)
            .join(SubscriptionLine, SubscriptionLine.subscription_id == Subscription.id)
            .filter(Subscription.status == SubscriptionStatus.active)
            .group_by(Plan.id, Plan.billing_interval)
            .all()
        )
        return {plan_id: float(total) * PERIODS_PER_MONTH[interval] for plan_id, interval, total in rows}

    def summary(self, date_from: date = None, date_to: date = None, plan_id=None) -> dict:
        """Figures for a period, this month by default. Optionally for one plan."""
        today = date.today()
        period_from = date_from or today.replace(day=1)
        period_to = date_to or today
        balance = Invoice.grand_total - Invoice.amount_paid

        subscriptions = self.db.query(Subscription.status, func.count(Subscription.id))
        if plan_id:
            subscriptions = subscriptions.filter(Subscription.plan_id == plan_id)
        by_status = {s.value: n for s, n in subscriptions.group_by(Subscription.status).all()}

        revenue, payment_count = self._payments(
            [func.coalesce(func.sum(Payment.amount), 0), func.count(Payment.id)],
            period_from, period_to, plan_id,
        ).one()

        outstanding = (
            self._for_plan(self.db.query(func.coalesce(func.sum(balance), 0)), plan_id)
            .filter(Invoice.status == InvoiceStatus.confirmed)
            .scalar()
        )

        overdue_count, overdue_amount = (
            self._for_plan(
                self.db.query(func.count(Invoice.id), func.coalesce(func.sum(balance), 0)), plan_id
            )
            .filter(*self._overdue_filter(today, date_from, date_to))
            .one()
        )

        mrr = self._mrr_by_plan()

        return {
            "period_from": str(period_from),
            "period_to": str(period_to),
            "active_subscription_count": by_status.get(SubscriptionStatus.active.value, 0),
            "subscriptions_by_status": by_status,
            "monthly_recurring_revenue": round(mrr.get(plan_id, 0) if plan_id else sum(mrr.values()), 2),
            "total_revenue_this_month": float(revenue),
            "payment_count": int(payment_count),
            "outstanding_amount": float(outstanding),
            "overdue_invoice_count": int(overdue_count),
            "overdue_amount": float(overdue_amount),
        }

    def revenue_by_month(self, date_from: date, date_to: date, plan_id=None) -> list:
        """DB-aggregated monthly revenue — uses DATE_TRUNC for Postgres efficiency."""
        month = func.date_trunc("month", Payment.payment_date).label("month")
        rows = (
            self._payments([month, func.sum(Payment.amount).label("total")], date_from, date_to, plan_id)
            .group_by(month)
            .order_by(month)
            .all()
        )
        return [
            {"month": r.month.strftime("%Y-%m"), "revenue": float(r.total)}
            for r in rows
        ]

    def payments_by_method(self, date_from: date, date_to: date, plan_id=None) -> list:
        rows = (
            self._payments(
                [Payment.method, func.sum(Payment.amount), func.count(Payment.id)],
                date_from, date_to, plan_id,
            )
            .group_by(Payment.method)
            .all()
        )
        return [
            {"method": method.value, "total": float(total), "count": count}
            for method, total, count in rows
        ]

    def by_plan(self, date_from: date, date_to: date) -> list:
        counts = {}
        for plan_id, status, count in (
            self.db.query(Subscription.plan_id, Subscription.status, func.count(Subscription.id))
            .group_by(Subscription.plan_id, Subscription.status)
            .all()
        ):
            counts.setdefault(plan_id, {})[status.value] = count

        received = dict(
            self._payments([Subscription.plan_id, func.sum(Payment.amount)], date_from, date_to)
            .join(Invoice, Payment.invoice_id == Invoice.id)
            .join(Subscription, Invoice.subscription_id == Subscription.id)
            .group_by(Subscription.plan_id)
            .all()
        )
        mrr = self._mrr_by_plan()
        return [
            {
                "plan_id": str(plan.id),
                "name": plan.name,
                "billing_interval": plan.billing_interval.value,
                "is_active": plan.is_active,
                "active": counts.get(plan.id, {}).get("active", 0),
                "paused": counts.get(plan.id, {}).get("paused", 0),
                "closed": counts.get(plan.id, {}).get("closed", 0),
                "mrr": round(mrr.get(plan.id, 0), 2),
                "received": float(received.get(plan.id, 0)),
            }
            for plan in self.db.query(Plan).order_by(Plan.name).all()
        ]

    def overdue_invoices(self, page) -> list:
        today = date.today()
        query = self.db.query(Invoice).filter(*self._overdue_filter(today))
        return [
            {
                "invoice_id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "customer_id": str(inv.customer_id),
                "customer_name": inv.customer_name,
                "customer_email": inv.customer_email,
                "grand_total": float(inv.grand_total),
                "balance_due": float(inv.balance_due),
                "due_date": str(inv.due_date),
                "days_overdue": (today - inv.due_date).days,
            }
            for inv in page.apply(query, Invoice.due_date.asc())
        ]

    def upcoming_renewals(self, page, days: int) -> list:
        """Active subscriptions ending soon, including any already past their end date."""
        today = date.today()
        query = self.db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.active,
            Subscription.expiry_date.isnot(None),
            Subscription.expiry_date <= today + timedelta(days=days),
        )
        return [
            {
                "subscription_id": str(sub.id),
                "subscription_number": sub.subscription_number,
                "customer_id": str(sub.customer_id),
                "customer_name": sub.customer_name,
                "plan_name": sub.plan_name,
                "expiry_date": str(sub.expiry_date),
                "days_left": (sub.expiry_date - today).days,
                "can_renew": sub.plan.can_renew,
            }
            for sub in page.apply(query, Subscription.expiry_date.asc())
        ]
