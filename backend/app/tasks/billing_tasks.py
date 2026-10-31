from datetime import date, datetime, timezone
from sqlalchemy import or_
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.subscription import Subscription, SubscriptionStatus
from app.services.invoicing_service import AlreadyBilledError, InvoicingService, NotBillableError
from app.utils.email import send_email
from app.utils.pdf import generate_invoice_pdf

# Most invoices one subscription gets in a single run after a long outage; the
# rest follow on the next run, so a daily plan cannot flood one customer at once
MAX_CATCH_UP_PERIODS = 24


def _deliver(db, invoice) -> bool:
    sent = send_email(
        to=invoice.customer_email,
        subject=f"Brightloop — Invoice {invoice.invoice_number}",
        body=(
            f"Dear {invoice.customer_name or invoice.customer_email},\n\n"
            f"Your invoice {invoice.invoice_number} for "
            f"{invoice.subscription_number} is ready.\n"
            f"Amount: {invoice.grand_total}\n"
            f"Due: {invoice.due_date}\n\n"
            "Thank you for being a Brightloop customer."
        ),
        attachment=generate_invoice_pdf(invoice),
        attachment_name=f"{invoice.invoice_number}.pdf",
    )
    if sent:
        invoice.sent_at = datetime.now(timezone.utc)
        db.add(invoice)
        db.commit()
    return sent


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_billing_cycle(self):
    """
    Daily billing task — runs at midnight UTC.
    Bills every period due on active subscriptions, confirms the invoices and emails
    them. Each subscription stands alone: one failure is logged and the run carries on.
    Safe to re-run: a period already billed is simply not due any more.
    """
    db = SessionLocal()
    results = {"success": [], "skipped": [], "failed": [], "email_failed": []}
    try:
        today = date.today()
        due = (
            db.query(Subscription.id)
            .filter(
                Subscription.status == SubscriptionStatus.active,
                Subscription.next_billing_date <= today,
                or_(
                    Subscription.expiry_date.is_(None),
                    Subscription.expiry_date >= Subscription.next_billing_date,
                ),
            )
            .order_by(Subscription.next_billing_date, Subscription.id)
            .all()
        )

        service = InvoicingService(db)

        for (subscription_id,) in due:
            key = str(subscription_id)
            billed = 0
            try:
                while billed < MAX_CATCH_UP_PERIODS:
                    invoice = service.generate_for_subscription(
                        subscription_id, auto_confirm=True, reissue=False
                    )
                    billed += 1
                    results["success"].append(key)
                    try:
                        delivered = _deliver(db, invoice)
                    except Exception:
                        db.rollback()
                        delivered = False
                    if not delivered:
                        results["email_failed"].append(invoice.invoice_number)
            except (AlreadyBilledError, NotBillableError):
                db.rollback()
                if not billed:
                    results["skipped"].append(key)
            except Exception as exc:
                db.rollback()
                results["failed"].append({"subscription_id": key, "error": str(exc)[:300]})

        return results

    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        db.close()
