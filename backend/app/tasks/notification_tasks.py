from datetime import date, timedelta
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.invoice import Invoice, InvoiceStatus
from app.models.subscription import Subscription, SubscriptionStatus
from app.utils.email import send_email


@celery_app.task
def send_overdue_reminders():
    """
    Daily at 9am UTC: email customers with overdue (confirmed, past due) invoices.
    """
    db = SessionLocal()
    try:
        today = date.today()
        invoices = (
            db.query(Invoice)
            .filter(
                Invoice.status == InvoiceStatus.confirmed,
                Invoice.due_date < today,
            )
            .all()
        )
        sent = 0
        for inv in invoices:
            days = (today - inv.due_date).days
            sent += send_email(
                to=inv.customer.email,
                subject=f"Brightloop — Overdue Invoice {inv.invoice_number}",
                body=(
                    f"Dear {inv.customer.full_name or inv.customer.email},\n\n"
                    f"Your invoice {inv.invoice_number} has {inv.balance_due} unpaid and "
                    f"was due on {inv.due_date} ({days} day(s) ago).\n\n"
                    "Please arrange payment at your earliest convenience to avoid service interruption.\n\n"
                    "Brightloop Software"
                ),
            )
        return {"overdue_reminders_sent": sent}
    finally:
        db.close()


@celery_app.task
def send_renewal_reminders():
    """
    Daily at 9:05am UTC: remind customers whose subscription expires in exactly 7 days.
    """
    db = SessionLocal()
    try:
        target_date = date.today() + timedelta(days=7)
        subs = (
            db.query(Subscription)
            .filter(
                Subscription.status == SubscriptionStatus.active,
                Subscription.expiry_date == target_date,
            )
            .all()
        )
        sent = 0
        for sub in subs:
            sent += send_email(
                to=sub.customer.email,
                subject="Brightloop — Your Subscription Is Expiring Soon",
                body=(
                    f"Dear {sub.customer.full_name or sub.customer.email},\n\n"
                    f"Your subscription {sub.subscription_number} will expire on {sub.expiry_date}.\n\n"
                    "You can renew from your portal once it ends, or talk to our team to continue without a break.\n\n"
                    "Brightloop Software"
                ),
            )
        return {"renewal_reminders_sent": sent}
    finally:
        db.close()

