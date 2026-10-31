from datetime import date
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.subscription import Subscription, SubscriptionStatus
from app.services.interval import next_billing_date_for


class SubscriptionService:
    """
    Subscription state-machine service.
    Valid transitions:
      draft ──► quotation ──► confirmed ──► active ──► paused ──► active
                                                    └──► closed ──► active (renew)
    """

    def __init__(self, db: Session):
        self.db = db

    def _get(self, subscription_id) -> Subscription:
        sub = self.db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return sub

    def send_to_quotation(self, subscription_id) -> Subscription:
        sub = self._get(subscription_id)
        if sub.status != SubscriptionStatus.draft:
            raise HTTPException(400, f"Cannot move to quotation from status '{sub.status}'")
        sub.status = SubscriptionStatus.quotation
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def confirm(self, subscription_id) -> Subscription:
        sub = self._get(subscription_id)
        if sub.status not in (SubscriptionStatus.draft, SubscriptionStatus.quotation):
            raise HTTPException(400, f"Cannot confirm from status '{sub.status}'")
        sub.status = SubscriptionStatus.confirmed
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def activate(self, subscription_id) -> Subscription:
        sub = self._get(subscription_id)
        if sub.status != SubscriptionStatus.confirmed:
            raise HTTPException(400, f"Cannot activate from status '{sub.status}'")
        sub.status = SubscriptionStatus.active
        sub.start_date = sub.start_date or date.today()
        # Set next_billing_date to today so billing task picks it up immediately
        sub.next_billing_date = sub.next_billing_date or date.today()
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def pause(self, subscription_id) -> Subscription:
        sub = self._get(subscription_id)
        if sub.status != SubscriptionStatus.active:
            raise HTTPException(400, "Only active subscriptions can be paused")
        if not sub.plan.can_pause:
            raise HTTPException(400, "This plan does not allow pausing")
        sub.status = SubscriptionStatus.paused
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def resume(self, subscription_id) -> Subscription:
        sub = self._get(subscription_id)
        if sub.status != SubscriptionStatus.paused:
            raise HTTPException(400, "Only paused subscriptions can be resumed")
        sub.status = SubscriptionStatus.active
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def close(self, subscription_id) -> Subscription:
        sub = self._get(subscription_id)
        if sub.status != SubscriptionStatus.active:
            raise HTTPException(400, "Only active subscriptions can be closed")
        expired = sub.expiry_date and sub.expiry_date <= date.today()
        if not (sub.plan.can_close_early or expired):
            raise HTTPException(400, "This plan does not allow early closure")
        sub.status = SubscriptionStatus.closed
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def renew(self, subscription_id) -> Subscription:
        sub = self._get(subscription_id)
        if sub.status != SubscriptionStatus.closed:
            raise HTTPException(400, "Only closed subscriptions can be renewed")
        if not sub.plan.can_renew:
            raise HTTPException(400, "This plan does not allow renewal")
        sub.status = SubscriptionStatus.active
        sub.start_date = date.today()
        sub.next_billing_date = next_billing_date_for(
            sub.plan.billing_interval, date.today()
        )
        self.db.commit()
        self.db.refresh(sub)
        return sub

