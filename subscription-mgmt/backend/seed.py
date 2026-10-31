"""
seed.py — Populate the database with demo data for development/testing.
Run: python seed.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from datetime import date
from decimal import Decimal
from app.core.database import SessionLocal, Base, engine
from app.core.security import hash_password
from app.models import (
    User, UserRole,
    Product, ProductVariant,
    Plan, BillingInterval,
    QuotationTemplate,
    Subscription, SubscriptionLine, SubscriptionStatus,
    TaxRule, TaxAppliesTo,
    Discount, DiscountType, DiscountScope,
)
from app.services.numbering import generate_subscription_number

Base.metadata.create_all(bind=engine)
db = SessionLocal()

print("Seeding database...")

# ── Users ─────────────────────────────────────────────────────────────────────
admin = User(email="admin@brightloop.test", full_name="Admin User",
             password_hash=hash_password("Admin@123"), role=UserRole.admin)
staff = User(email="staff@brightloop.test", full_name="Sales Staff",
             password_hash=hash_password("Staff@123"), role=UserRole.staff)
customer1 = User(email="alice@acme.test", full_name="Alice Johnson",
                 password_hash=hash_password("Alice@123"), role=UserRole.customer)
customer2 = User(email="bob@globex.test", full_name="Bob Smith",
                 password_hash=hash_password("Bob@1234"), role=UserRole.customer)
db.add_all([admin, staff, customer1, customer2])
db.flush()

# ── Products ──────────────────────────────────────────────────────────────────
erp = Product(name="Brightloop ERP", type="Software",
               sales_price=Decimal("2000"), cost_price=Decimal("500"),
               notes="Full ERP suite for SMEs")
addon = Product(name="Analytics Add-on", type="Add-on",
                sales_price=Decimal("500"), cost_price=Decimal("100"))
db.add_all([erp, addon])
db.flush()

odoo_variant = ProductVariant(product_id=erp.id, label="Odoo Edition", price_delta=Decimal("560"))
db.add(odoo_variant)
db.flush()

# ── Plans ──────────────────────────────────────────────────────────────────────
monthly_plan = Plan(
    name="ERP Monthly", product_id=erp.id,
    billing_interval=BillingInterval.monthly,
    price=Decimal("2000"), min_quantity=1,
    available_from=date(2026, 1, 1),
    can_pause=True, can_close_early=True, can_renew=True,
)
yearly_plan = Plan(
    name="ERP Yearly", product_id=erp.id,
    billing_interval=BillingInterval.yearly,
    price=Decimal("20000"), min_quantity=1,
    available_from=date(2026, 1, 1),
    auto_close=False, can_pause=True, can_close_early=False, can_renew=True,
)
db.add_all([monthly_plan, yearly_plan])
db.flush()

# ── Quotation Template ─────────────────────────────────────────────────────────
tpl = QuotationTemplate(name="Standard ERP Monthly", plan_id=monthly_plan.id,
                        validity_days=30, notes="Default template for ERP monthly offers")
db.add(tpl)
db.flush()

# ── Tax Rules ─────────────────────────────────────────────────────────────────
global_tax = TaxRule(name="GST 18%", rate=Decimal("0.1800"), applies_to=TaxAppliesTo.all)
db.add(global_tax)
db.flush()

# ── Discounts ────────────────────────────────────────────────────────────────
promo = Discount(
    name="New Customer 10% Off", type=DiscountType.percentage,
    value=Decimal("10"), start_date=date(2026, 10, 1),
    end_date=date(2026, 12, 31), max_uses=100,
    scope=DiscountScope.subscription,
)
db.add(promo)
db.flush()

# ── Subscriptions ─────────────────────────────────────────────────────────────
sub1 = Subscription(
    subscription_number=generate_subscription_number(db),
    customer_id=customer1.id,
    plan_id=monthly_plan.id,
    template_id=tpl.id,
    status=SubscriptionStatus.active,
    start_date=date(2026, 10, 1),
    expiry_date=date(2027, 9, 30),
    next_billing_date=date(2026, 11, 1),
    payment_terms=15,
    created_by=staff.id,
)
db.add(sub1)
db.flush()

db.add(SubscriptionLine(
    subscription_id=sub1.id, product_id=erp.id,
    quantity=2, unit_price=Decimal("2000"),
    line_total=Decimal("4000"),
))

sub2 = Subscription(
    subscription_number=generate_subscription_number(db),
    customer_id=customer2.id,
    plan_id=yearly_plan.id,
    status=SubscriptionStatus.draft,
    payment_terms=30,
    created_by=staff.id,
)
db.add(sub2)
db.flush()

db.commit()
print("✅ Seed complete.")
print("\nDemo accounts:")
print("  Admin  : admin@brightloop.test  / Admin@123")
print("  Staff  : staff@brightloop.test  / Staff@123")
print("  Customer: alice@acme.test       / Alice@123")
print("  Customer: bob@globex.test       / Bob@1234")

