"""
seed.py — Populate the database with demo data for development/testing.
Run: python seed.py (after: alembic upgrade head)
Does nothing if the database already has users.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta
from decimal import Decimal
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    User, UserRole,
    Product, ProductVariant,
    Plan, BillingInterval,
    QuotationTemplate, QuotationTemplateLine,
    Subscription, SubscriptionLine, SubscriptionStatus,
    TaxRule, TaxAppliesTo,
    Discount, DiscountType, DiscountScope,
)
from app.services.numbering import generate_subscription_number


def run():
    db = SessionLocal()
    try:
        if db.query(User).first():
            print("Database already has users; skipping demo data.")
            return

        print("Seeding database...")
        today = date.today()

        # ── Users ─────────────────────────────────────────────────────────────
        admin = User(email="admin@brightloop.test", full_name="Admin User",
                     password_hash=hash_password("Admin@123"), role=UserRole.admin)
        staff = User(email="staff@brightloop.test", full_name="Sales Staff",
                     password_hash=hash_password("Staff@123"), role=UserRole.staff)
        customer1 = User(email="alice@acme.test", full_name="Alice Johnson",
                         company_name="Acme Traders", phone="+91 98000 11111",
                         address="12 MG Road, Kochi",
                         password_hash=hash_password("Alice@123"), role=UserRole.customer)
        customer2 = User(email="bob@globex.test", full_name="Bob Smith",
                         company_name="Globex Ltd",
                         password_hash=hash_password("Bob@12345"), role=UserRole.customer)
        db.add_all([admin, staff, customer1, customer2])
        db.flush()

        # ── Products ──────────────────────────────────────────────────────────
        erp = Product(name="Brightloop ERP", type="Software",
                      sales_price=Decimal("2000"), cost_price=Decimal("500"),
                      notes="Full ERP suite for SMEs")
        addon = Product(name="Analytics Add-on", type="Add-on",
                        sales_price=Decimal("500"), cost_price=Decimal("100"))
        db.add_all([erp, addon])
        db.flush()

        odoo_variant = ProductVariant(product_id=erp.id, label="Odoo", price_delta=Decimal("560"))
        db.add(odoo_variant)
        db.flush()

        # ── Plans ─────────────────────────────────────────────────────────────
        monthly_plan = Plan(
            name="ERP Monthly", product_id=erp.id,
            billing_interval=BillingInterval.monthly,
            price=Decimal("2000"), min_quantity=1,
            available_from=today - timedelta(days=90),
            can_pause=True, can_close_early=True, can_renew=True,
        )
        yearly_plan = Plan(
            name="ERP Yearly", product_id=erp.id,
            billing_interval=BillingInterval.yearly,
            price=Decimal("20000"), min_quantity=1,
            available_from=today - timedelta(days=90),
            auto_close=True, can_pause=False, can_close_early=False, can_renew=True,
        )
        db.add_all([monthly_plan, yearly_plan])
        db.flush()

        # ── Quotation Template ────────────────────────────────────────────────
        tpl = QuotationTemplate(name="Standard ERP Monthly", plan_id=monthly_plan.id,
                                validity_days=30, payment_terms=15,
                                notes="Default template for ERP monthly offers")
        tpl.lines = [
            QuotationTemplateLine(product_id=erp.id, quantity=2),
            QuotationTemplateLine(product_id=addon.id, quantity=1),
        ]
        db.add(tpl)
        db.flush()

        # ── Tax Rules ─────────────────────────────────────────────────────────
        db.add(TaxRule(name="GST 18%", rate=Decimal("0.1800"), applies_to=TaxAppliesTo.all))
        db.flush()

        # ── Discounts ─────────────────────────────────────────────────────────
        db.add(Discount(
            name="New Customer 10% Off", type=DiscountType.percentage,
            value=Decimal("10"), start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=60), max_uses=100,
            scope=DiscountScope.subscription,
        ))
        db.flush()

        # ── Subscriptions ─────────────────────────────────────────────────────
        start = today - timedelta(days=30)
        sub1 = Subscription(
            subscription_number=generate_subscription_number(db),
            customer_id=customer1.id,
            plan_id=monthly_plan.id,
            template_id=tpl.id,
            status=SubscriptionStatus.active,
            start_date=start,
            expiry_date=start + timedelta(days=364),
            next_billing_date=today,
            payment_terms=15,
            created_by=staff.id,
        )
        db.add(sub1)
        db.flush()

        db.add(SubscriptionLine(
            subscription_id=sub1.id, product_id=erp.id,
            quantity=2, unit_price=Decimal("2000"),
            tax_amount=Decimal("720"), line_total=Decimal("4720"),
        ))

        db.add(Subscription(
            subscription_number=generate_subscription_number(db),
            customer_id=customer2.id,
            plan_id=yearly_plan.id,
            status=SubscriptionStatus.draft,
            payment_terms=30,
            created_by=staff.id,
        ))

        db.commit()
        print("Seed complete.")
        print("\nDemo accounts:")
        print("  Admin   : admin@brightloop.test / Admin@123")
        print("  Staff   : staff@brightloop.test / Staff@123")
        print("  Customer: alice@acme.test       / Alice@123")
        print("  Customer: bob@globex.test       / Bob@12345")
    finally:
        db.close()


if __name__ == "__main__":
    run()
