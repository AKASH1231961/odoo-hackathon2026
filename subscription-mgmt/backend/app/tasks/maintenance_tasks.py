from datetime import date
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.discount import Discount


@celery_app.task
def auto_close_expired_plans():
    """
    Nightly: close plans where available_to < today AND auto_close=True.
    Matching the spec §3.3 auto-close background job.
    """
    db = SessionLocal()
    try:
        today = date.today()
        plans = (
            db.query(Plan)
            .filter(
                Plan.available_to.isnot(None),
                Plan.available_to < today,
                Plan.auto_close.is_(True),
                Plan.is_active.is_(True),
            )
            .all()
        )
        for plan in plans:
            plan.is_active = False
            db.add(plan)
        db.commit()
        return {"closed_plans": len(plans)}
    finally:
        db.close()


@celery_app.task
def auto_close_expired_subscriptions():
    """
    Nightly: close active subscriptions that have passed their expiry_date.
    """
    db = SessionLocal()
    try:
        today = date.today()
        subs = (
            db.query(Subscription)
            .filter(
                Subscription.status == SubscriptionStatus.active,
                Subscription.expiry_date.isnot(None),
                Subscription.expiry_date < today,
            )
            .all()
        )
        for sub in subs:
            sub.status = SubscriptionStatus.closed
            db.add(sub)
        db.commit()
        return {"closed_subscriptions": len(subs)}
    finally:
        db.close()


@celery_app.task
def expire_discounts():
    """
    Nightly: deactivate discounts whose end_date has passed.
    """
    db = SessionLocal()
    try:
        today = date.today()
        discounts = (
            db.query(Discount)
            .filter(
                Discount.end_date.isnot(None),
                Discount.end_date < today,
                Discount.is_active.is_(True),
            )
            .all()
        )
        for d in discounts:
            d.is_active = False
            db.add(d)
        db.commit()
        return {"expired_discounts": len(discounts)}
    finally:
        db.close()

