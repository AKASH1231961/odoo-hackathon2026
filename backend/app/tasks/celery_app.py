from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "subscription_mgmt",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.billing_tasks",
        "app.tasks.maintenance_tasks",
        "app.tasks.notification_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    # Billing cycle — runs at midnight UTC every day
    "run-billing-cycle-daily": {
        "task": "app.tasks.billing_tasks.run_billing_cycle",
        "schedule": crontab(hour=0, minute=0),
    },
    # Auto-close expired plans with auto_close=True
    "auto-close-expired-plans-daily": {
        "task": "app.tasks.maintenance_tasks.auto_close_expired_plans",
        "schedule": crontab(hour=0, minute=5),
    },
    # Auto-close subscriptions past their expiry_date
    "auto-close-expired-subscriptions-daily": {
        "task": "app.tasks.maintenance_tasks.auto_close_expired_subscriptions",
        "schedule": crontab(hour=0, minute=10),
    },
    # Deactivate expired discounts
    "expire-discounts-daily": {
        "task": "app.tasks.maintenance_tasks.expire_discounts",
        "schedule": crontab(hour=0, minute=15),
    },
    # Overdue invoice reminders at 9am UTC
    "send-overdue-reminders-daily": {
        "task": "app.tasks.notification_tasks.send_overdue_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
    # Subscription renewal reminders (7 days ahead) at 9:05am UTC
    "send-renewal-reminders-daily": {
        "task": "app.tasks.notification_tasks.send_renewal_reminders",
        "schedule": crontab(hour=9, minute=5),
    },
}


