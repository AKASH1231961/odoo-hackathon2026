from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.plan import Plan
from app.models.product import Product, ProductVariant
from app.models.quotation_template import QuotationTemplate
from app.models.subscription import (
    Subscription,
    SubscriptionLine,
    SubscriptionStatus,
    SubscriptionStatusHistory,
)
from app.models.user import User, UserRole
from app.services.interval import next_billing_date_for
from app.services.numbering import generate_subscription_number
from app.services.tax_calculator import TaxCalculator

DEFAULT_QUOTATION_DAYS = 30
DEFAULT_PAYMENT_TERMS = 15


class SubscriptionService:
    """
    Subscription creation and state-machine service.
    Valid transitions:
      draft ──► quotation ──► confirmed ──► active ──► paused ──► active
                                                    └──► closed ──► active (renew)
    paused subscriptions may also be closed.
    """

    def __init__(self, db: Session):
        self.db = db

    def _get(self, subscription_id) -> Subscription:
        sub = self.db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return sub

    def _change_status(self, sub, status, changed_by=None) -> Subscription:
        previous_status = sub.status
        sub.status = status
        self.db.add(
            SubscriptionStatusHistory(
                subscription_id=sub.id,
                from_status=previous_status,
                to_status=status,
                changed_by=changed_by,
            )
        )
        self.db.commit()
        self.db.refresh(sub)
        return sub

    # ── Creation ──────────────────────────────────────────────────────────────

    def _sellable_plan(self, plan_id) -> Plan:
        plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            raise HTTPException(404, "Plan not found")
        if not plan.is_active:
            raise HTTPException(400, "This plan is closed")
        today = date.today()
        if plan.available_from and plan.available_from > today:
            raise HTTPException(400, f"This plan is not available until {plan.available_from}")
        if plan.available_to and plan.available_to < today:
            raise HTTPException(400, f"This plan stopped being available on {plan.available_to}")
        return plan

    def _variant(self, variant_id, product_id):
        if not variant_id:
            return None
        variant = (
            self.db.query(ProductVariant)
            .filter(ProductVariant.id == variant_id, ProductVariant.product_id == product_id)
            .first()
        )
        if not variant or not variant.is_active:
            raise HTTPException(400, "That variant is not available for this product")
        return variant

    def _line(self, plan, product_id, quantity, unit_price=None, variant_id=None) -> SubscriptionLine:
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product or not product.is_active:
            raise HTTPException(400, "That product is not available")
        variant = self._variant(variant_id, product_id)

        if unit_price is None:
            base = plan.price if product_id == plan.product_id else product.sales_price
            delta = variant.price_delta if variant else 0
            unit_price = Decimal(str(base)) + Decimal(str(delta))

        amount = Decimal(str(unit_price)) * quantity
        tax = TaxCalculator(self.db).calculate(product_id, amount, plan_id=plan.id)
        return SubscriptionLine(
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
            unit_price=unit_price,
            tax_amount=tax,
            line_total=amount + tax,
        )

    def _check_minimum(self, plan, lines):
        quantity = sum(l.quantity for l in lines if l.product_id == plan.product_id)
        if quantity < plan.min_quantity:
            raise HTTPException(400, f"This plan needs a minimum quantity of {plan.min_quantity}")

    def create(self, payload, created_by) -> Subscription:
        customer = self.db.query(User).filter(User.id == payload.customer_id).first()
        if not customer or customer.role != UserRole.customer or not customer.is_active:
            raise HTTPException(400, "Subscriptions can only belong to an active customer")

        template = None
        if payload.template_id:
            template = (
                self.db.query(QuotationTemplate)
                .filter(QuotationTemplate.id == payload.template_id)
                .first()
            )
            if not template:
                raise HTTPException(404, "Quotation template not found")

        plan_id = payload.plan_id or (template.plan_id if template else None)
        if not plan_id:
            raise HTTPException(400, "Choose a plan or a quotation template")
        plan = self._sellable_plan(plan_id)
        variant = self._variant(payload.variant_id, plan.product_id)

        if payload.lines:
            source = [
                (l.product_id, l.quantity, l.unit_price, l.variant_id) for l in payload.lines
            ]
        elif template and template.lines:
            source = [
                (l.product_id, l.quantity, l.unit_price, l.variant_id) for l in template.lines
            ]
        else:
            source = [(plan.product_id, plan.min_quantity, None, None)]

        lines = [
            self._line(
                plan, product_id, quantity, unit_price,
                variant_id or (variant.id if variant and product_id == plan.product_id else None),
            )
            for product_id, quantity, unit_price, variant_id in source
        ]
        self._check_minimum(plan, lines)

        terms = payload.payment_terms
        if terms is None:
            terms = template.payment_terms if template else DEFAULT_PAYMENT_TERMS

        sub = Subscription(
            subscription_number=generate_subscription_number(self.db),
            customer_id=customer.id,
            plan_id=plan.id,
            variant_id=payload.variant_id,
            template_id=payload.template_id,
            start_date=payload.start_date,
            expiry_date=payload.expiry_date,
            payment_terms=terms,
            status=SubscriptionStatus.draft,
            created_by=created_by,
            lines=lines,
        )
        self.db.add(sub)
        self.db.flush()
        self.db.add(
            SubscriptionStatusHistory(
                subscription_id=sub.id,
                from_status=None,
                to_status=SubscriptionStatus.draft,
                changed_by=created_by,
            )
        )
        self.db.commit()
        self.db.refresh(sub)
        return sub

    # ── Lines (add-ons) ───────────────────────────────────────────────────────

    def _editable(self, subscription_id) -> Subscription:
        sub = self._get(subscription_id)
        if sub.status == SubscriptionStatus.closed:
            raise HTTPException(400, "A closed subscription cannot be changed")
        return sub

    def add_line(self, subscription_id, product_id, quantity, unit_price=None, variant_id=None):
        sub = self._editable(subscription_id)
        if any(l.product_id == product_id and l.variant_id == variant_id for l in sub.lines):
            raise HTTPException(400, "That product is already on this subscription")
        sub.lines.append(self._line(sub.plan, product_id, quantity, unit_price, variant_id))
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def _find_line(self, sub, line_id) -> SubscriptionLine:
        line = next((l for l in sub.lines if l.id == line_id), None)
        if not line:
            raise HTTPException(404, "Line not found")
        return line

    def update_line(self, subscription_id, line_id, quantity):
        sub = self._editable(subscription_id)
        line = self._find_line(sub, line_id)
        line.quantity = quantity
        self._check_minimum(sub.plan, sub.lines)
        amount = Decimal(str(line.unit_price)) * quantity
        line.tax_amount = TaxCalculator(self.db).calculate(line.product_id, amount, plan_id=sub.plan_id)
        line.line_total = amount + line.tax_amount
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def remove_line(self, subscription_id, line_id):
        sub = self._editable(subscription_id)
        line = self._find_line(sub, line_id)
        if line.product_id == sub.plan.product_id:
            raise HTTPException(400, "The plan's own product cannot be removed")
        sub.lines.remove(line)
        self.db.commit()
        self.db.refresh(sub)
        return sub

    # ── Transitions ───────────────────────────────────────────────────────────

    def send_to_quotation(self, subscription_id, changed_by=None) -> Subscription:
        sub = self._get(subscription_id)
        if sub.status != SubscriptionStatus.draft:
            raise HTTPException(400, f"Cannot move to quotation from status '{sub.status.value}'")
        days = sub.template.validity_days if sub.template else DEFAULT_QUOTATION_DAYS
        sub.quotation_valid_until = date.today() + timedelta(days=days)
        return self._change_status(sub, SubscriptionStatus.quotation, changed_by)

    def confirm(self, subscription_id, changed_by=None) -> Subscription:
        sub = self._get(subscription_id)
        if sub.status != SubscriptionStatus.quotation:
            raise HTTPException(400, f"Cannot confirm from status '{sub.status.value}'")
        if sub.quotation_valid_until and sub.quotation_valid_until < date.today():
            raise HTTPException(400, f"This quotation expired on {sub.quotation_valid_until}")
        return self._change_status(sub, SubscriptionStatus.confirmed, changed_by)

    def activate(self, subscription_id, changed_by=None) -> Subscription:
        sub = self._get(subscription_id)
        if sub.status != SubscriptionStatus.confirmed:
            raise HTTPException(400, f"Cannot activate from status '{sub.status.value}'")
        today = date.today()
        if sub.expiry_date and sub.expiry_date < (sub.start_date or today):
            raise HTTPException(400, "The expiry date has already passed")
        sub.start_date = sub.start_date or today
        # First invoice is due on the start date, or today if that has passed
        sub.next_billing_date = sub.next_billing_date or max(sub.start_date, today)
        return self._change_status(sub, SubscriptionStatus.active, changed_by)

    def pause(self, subscription_id, changed_by=None) -> Subscription:
        sub = self._get(subscription_id)
        if sub.status != SubscriptionStatus.active:
            raise HTTPException(400, "Only active subscriptions can be paused")
        if not sub.plan.can_pause:
            raise HTTPException(400, "This plan does not allow pausing")
        return self._change_status(sub, SubscriptionStatus.paused, changed_by)

    def resume(self, subscription_id, changed_by=None) -> Subscription:
        sub = self._get(subscription_id)
        if sub.status != SubscriptionStatus.paused:
            raise HTTPException(400, "Only paused subscriptions can be resumed")
        # Periods that passed while paused are not billed
        today = date.today()
        while sub.next_billing_date and sub.next_billing_date < today:
            sub.next_billing_date = next_billing_date_for(
                sub.plan.billing_interval, sub.next_billing_date, anchor=sub.start_date
            )
        return self._change_status(sub, SubscriptionStatus.active, changed_by)

    def close(self, subscription_id, changed_by=None) -> Subscription:
        sub = self._get(subscription_id)
        if sub.status not in (SubscriptionStatus.active, SubscriptionStatus.paused):
            raise HTTPException(400, "Only active or paused subscriptions can be closed")
        expired = sub.expiry_date and sub.expiry_date <= date.today()
        if not (sub.plan.can_close_early or expired):
            raise HTTPException(400, "This plan does not allow early closure")
        return self._change_status(sub, SubscriptionStatus.closed, changed_by)

    def renew(self, subscription_id, changed_by=None) -> Subscription:
        sub = self._get(subscription_id)
        if sub.status != SubscriptionStatus.closed:
            raise HTTPException(400, "Only closed subscriptions can be renewed")
        if not sub.plan.can_renew:
            raise HTTPException(400, "This plan does not allow renewal")
        if not sub.plan.is_active:
            raise HTTPException(400, "This plan is closed")

        today = date.today()
        if sub.expiry_date:
            # A new term of the same length as the last one
            if sub.start_date and sub.expiry_date > sub.start_date:
                term = sub.expiry_date - sub.start_date
            else:
                term = next_billing_date_for(sub.plan.billing_interval, today) - today
            sub.expiry_date = today + term
        sub.start_date = today
        sub.next_billing_date = today
        return self._change_status(sub, SubscriptionStatus.active, changed_by)
