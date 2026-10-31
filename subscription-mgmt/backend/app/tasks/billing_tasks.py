from datetime import date
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.subscription import Subscription, SubscriptionStatus
from app.services.invoicing_service import InvoicingService, AlreadyBilledError
from app.utils.email import send_email
from app.utils.pdf import generate_invoice_pdf


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_billing_cycle(self):
    """
    Daily billing task — runs at midnight UTC.
    Finds all active subscriptions due for billing today, generates invoices,
    and emails them to customers. Logs success/failure per subscription.
    Idempotent: AlreadyBilledError is silently skipped.
    """
    db = SessionLocal()
    results = {"success": [], "skipped": [], "failed": []}
    try:
        today = date.today()
        subs = (
            db.query(Subscription)
            .filter(
                Subscription.status == SubscriptionStatus.active,
                Subscription.next_billing_date <= today,
            )
            .all()
        )

        service = InvoicingService(db)

        for sub in subs:
            try:
                invoice = service.generate_for_subscription(sub.id)

                # Auto-confirm the draft invoice
                from app.models.invoice import InvoiceStatus
                from datetime import datetime
                invoice.status = InvoiceStatus.confirmed
                invoice.issued_at = datetime.utcnow()
                db.add(invoice)
                db.commit()
                db.refresh(invoice)

                pdf_bytes = generate_invoice_pdf(invoice)
                send_email(
                    to=sub.customer.email,
                    subject=f"Brightloop — Invoice {invoice.invoice_number}",
                    body=(
                        f"Dear {sub.customer.full_name or sub.customer.email},\n\n"
                        f"Your invoice {invoice.invoice_number} for "
                        f"{sub.subscription_number} is ready.\n"
                        f"Amount: {invoice.grand_total}\n"
                        f"Due: {invoice.due_date}\n\n"
                        "Thank you for being a Brightloop customer."
                    ),
                    attachment=pdf_bytes,
                    attachment_name=f"{invoice.invoice_number}.pdf",
                )
                results["success"].append(str(sub.id))

            except AlreadyBilledError:
                results["skipped"].append(str(sub.id))
            except Exception as exc:
                results["failed"].append({"subscription_id": str(sub.id), "error": str(exc)})

        return results

    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        db.close()

