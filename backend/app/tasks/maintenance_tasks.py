from datetime import date
from sqlalchemy import and_, or_
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.plan import Plan
from app.models.subscription import (
    Subscription,
    SubscriptionStatus,
    SubscriptionStatusHistory,
)
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
    Nightly: close subscriptions on auto_close plans once they end, at their expiry_date
    or, if they have none, at the plan's end date. Other plans stay open for the team
    to close or renew; billing stops at the expiry date either way.
    """
    db = SessionLocal()
    try:
        today = date.today()
        subs = (
            db.query(Subscription)
            .join(Plan, Subscription.plan_id == Plan.id)
            .filter(
                Subscription.status.in_([SubscriptionStatus.active, SubscriptionStatus.paused]),
                Plan.auto_close.is_(True),
                or_(
                    Subscription.expiry_date < today,
                    and_(Subscription.expiry_date.is_(None), Plan.available_to < today),
                ),
            )
            .all()
        )
        for sub in subs:
            db.add(
                SubscriptionStatusHistory(
                    subscription_id=sub.id,
                    from_status=sub.status,
                    to_status=SubscriptionStatus.closed,
                )
            )
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
