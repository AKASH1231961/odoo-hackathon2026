"""End-to-end rules from the problem statement, through the API."""
import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

import pytest

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.invoice import Invoice
from app.services.interval import next_billing_date_for
from app.models.plan import BillingInterval
from app.tasks import billing_tasks
from app.tasks.billing_tasks import run_billing_cycle
from app.tasks.maintenance_tasks import auto_close_expired_subscriptions

PASSWORD = "Passw0rd@1"


def day(offset=0):
    return (date.today() + timedelta(days=offset)).isoformat()


@pytest.fixture
def world(client, db):
    """Admin, staff, two customers, a 1000/month product and an 18% tax rule."""
    class World:
        pass

    w = World()
    w.client = client
    w.db = db

    def user(role):
        u = User(email=f"{uuid.uuid4().hex[:10]}@example.com", full_name=role,
                 password_hash=hash_password(PASSWORD), role=UserRole(role))
        db.add(u)
        db.commit()
        token = client.post("/auth/login", json={"email": u.email, "password": PASSWORD}).json()
        return u, {"Authorization": f"Bearer {token['access_token']}"}

    _, w.admin = user("admin")
    w.staff_user, w.staff = user("staff")
    w.alice, w.alice_h = user("customer")
    w.bob, w.bob_h = user("customer")

    def product(price="1000", **extra):
        r = client.post("/products", headers=w.admin, json={"name": "P", "sales_price": price, **extra})
        assert r.status_code == 201, r.text
        return r.json()

    def plan(prod=None, **extra):
        prod = prod or w.product
        body = {"name": "Plan", "product_id": prod["id"], "billing_interval": "monthly",
                "price": "1000", **extra}
        r = client.post("/plans", headers=w.admin, json=body)
        assert r.status_code == 201, r.text
        return r.json()

    def subscription(plan_=None, state="active", customer=None, **extra):
        body = {"customer_id": str((customer or w.alice).id), "plan_id": (plan_ or w.plan)["id"], **extra}
        r = client.post("/subscriptions", headers=w.staff, json=body)
        assert r.status_code == 201, r.text
        sub = r.json()
        for action, reached in (("quotation", "quotation"), ("confirm", "confirmed"), ("activate", "active")):
            if state == "draft":
                break
            r = client.post(f"/subscriptions/{sub['id']}/{action}", headers=w.staff)
            assert r.status_code == 200, r.text
            sub = r.json()
            if state == reached:
                break
        return sub

    def invoice(sub=None, confirm=True):
        sub = sub or subscription()
        r = client.post(f"/invoices/generate/{sub['id']}", headers=w.staff)
        assert r.status_code == 201, r.text
        inv = r.json()
        if confirm:
            inv = client.post(f"/invoices/{inv['id']}/confirm", headers=w.staff).json()
        return inv

    def discount(**extra):
        body = {"name": "D", "type": "percentage", "value": "10", "start_date": day(-1),
                "scope": "subscription", **extra}
        r = client.post("/discounts", headers=w.admin, json=body)
        assert r.status_code == 201, r.text
        return r.json()

    def pay(invoice_id, amount, **extra):
        body = {"invoice_id": invoice_id, "amount": str(amount), "method": "cash",
                "payment_date": day(), **extra}
        return client.post("/payments", headers=w.staff, json=body)

    w.make_product, w.make_plan, w.subscription = product, plan, subscription
    w.invoice, w.discount, w.pay = invoice, discount, pay
    w.product = product()
    w.plan = plan()
    client.post("/tax-rules", headers=w.admin, json={"name": "GST", "rate": "0.18"})
    return w


# ── Accounts ──────────────────────────────────────────────────────────────────

def test_password_must_be_more_than_eight_characters(client):
    bad = client.post("/auth/register", json={"email": "a@example.com", "password": "Abcdef@1"})
    good = client.post("/auth/register", json={"email": "a@example.com", "password": "Abcdefg@1"})
    assert (bad.status_code, good.status_code) == (422, 201)


def test_email_is_unique_regardless_of_case(client):
    client.post("/auth/register", json={"email": "Case@example.com", "password": "Abcdefg@1"})
    r = client.post("/auth/register", json={"email": "case@EXAMPLE.com", "password": "Abcdefg@1"})
    assert r.status_code == 400


def test_reserved_domain_accounts_can_sign_in(client, db):
    db.add(User(email="demo@brightloop.test", password_hash=hash_password(PASSWORD), role=UserRole.admin))
    db.commit()
    r = client.post("/auth/login", json={"email": "demo@brightloop.test", "password": PASSWORD})
    assert r.status_code == 200
    me = client.get("/users/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200


def test_password_reset_flow_and_single_use(client):
    client.post("/auth/register", json={"email": "r@example.com", "password": "Abcdefg@1"})
    with mock.patch("app.api.auth.send_email", return_value=True) as send:
        client.post("/auth/forgot-password", json={"email": "r@example.com"})
    token = send.call_args.args[2].split("token=")[1].split()[0]
    body = {"token": token, "new_password": "Newpass@123"}
    assert client.post("/auth/reset-password", json=body).status_code == 200
    assert client.post("/auth/reset-password", json=body).status_code == 400
    assert client.post("/auth/login", json={"email": "r@example.com", "password": "Newpass@123"}).status_code == 200


def test_repeated_failed_logins_are_blocked(client):
    codes = [
        client.post("/auth/login", json={"email": "x@example.com", "password": "Wrong@1234"}).status_code
        for _ in range(12)
    ]
    assert codes[0] == 401 and codes[-1] == 429


def test_validation_errors_are_readable_text(client):
    r = client.post("/auth/register", json={"email": "bad", "password": "x"})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


# ── Roles ─────────────────────────────────────────────────────────────────────

def test_only_admin_sets_up_catalogue(world):
    c = world.client
    assert c.post("/products", headers=world.staff, json={"name": "x", "sales_price": "1"}).status_code == 403
    body = {"name": "x", "product_id": world.product["id"], "billing_interval": "daily", "price": "1"}
    assert c.post("/plans", headers=world.staff, json=body).status_code == 403


def test_cost_price_is_hidden_from_customers_and_public(world):
    c = world.client
    assert c.get("/products").status_code == 401
    assert "cost_price" not in c.get("/products", headers=world.alice_h).json()[0]
    assert "cost_price" in c.get("/products", headers=world.staff).json()[0]


def test_customers_are_isolated_and_drafts_hidden(world):
    c = world.client
    draft = world.invoice(confirm=False)
    assert c.get("/portal/invoices", headers=world.alice_h).json() == []
    confirmed = world.invoice(world.subscription())
    assert len(c.get("/portal/invoices", headers=world.alice_h).json()) == 1
    assert c.get(f"/portal/invoices/{confirmed['id']}", headers=world.bob_h).status_code == 404
    assert c.get(f"/portal/invoices/{draft['id']}", headers=world.alice_h).status_code == 404


# ── Plans, quotes and subscriptions ───────────────────────────────────────────

def test_template_supplies_plan_lines_and_terms(world):
    c = world.client
    addon = world.make_product("500", type="Add-on")
    tpl = c.post("/quotation-templates", headers=world.staff, json={
        "name": "T", "plan_id": world.plan["id"], "validity_days": 7, "payment_terms": 45,
        "lines": [{"product_id": world.product["id"], "quantity": 2}, {"product_id": addon["id"]}],
    }).json()
    sub = c.post("/subscriptions", headers=world.staff, json={
        "customer_id": str(world.alice.id), "template_id": tpl["id"],
    }).json()
    assert sub["plan_id"] == world.plan["id"] and sub["payment_terms"] == 45
    assert sorted(float(l["unit_price"]) for l in sub["lines"]) == [500.0, 1000.0]
    quoted = c.post(f"/subscriptions/{sub['id']}/quotation", headers=world.staff).json()
    assert quoted["quotation_valid_until"] == day(7)


def test_expired_quotation_cannot_be_confirmed(world):
    sub = world.subscription(state="quotation")
    from app.models.subscription import Subscription
    row = world.db.get(Subscription, uuid.UUID(sub["id"]))
    row.quotation_valid_until = date.today() - timedelta(days=1)
    world.db.commit()
    assert world.client.post(f"/subscriptions/{sub['id']}/confirm", headers=world.staff).status_code == 400


@pytest.mark.parametrize("plan_args,line_qty", [
    ({"min_quantity": 5}, 1),
    ({"available_to": day(-1), "available_from": day(-9)}, 5),
])
def test_plan_rules_enforced_when_selling(world, plan_args, line_qty):
    plan = world.make_plan(**plan_args)
    r = world.client.post("/subscriptions", headers=world.staff, json={
        "customer_id": str(world.alice.id), "plan_id": plan["id"],
        "lines": [{"product_id": plan["product_id"], "quantity": line_qty}],
    })
    assert r.status_code == 400


def test_line_shows_tax_and_amount(world):
    line = world.subscription(state="draft")["lines"][0]
    assert (Decimal(line["tax_amount"]), Decimal(line["line_total"])) == (Decimal("180.00"), Decimal("1180.00"))


def test_renewal_starts_a_new_term_that_survives_the_nightly_close(world):
    sub = world.subscription(world.make_plan(auto_close=True), start_date=day(-40), expiry_date=day(-10))
    c = world.client
    c.post(f"/subscriptions/{sub['id']}/close", headers=world.staff)
    renewed = c.post(f"/subscriptions/{sub['id']}/renew", headers=world.staff).json()
    assert renewed["expiry_date"] == day(30)
    auto_close_expired_subscriptions()
    assert c.get(f"/subscriptions/{sub['id']}", headers=world.staff).json()["status"] == "active"


def test_auto_close_follows_the_plan_setting(world):
    closes = world.subscription(world.make_plan(auto_close=True), start_date=day(-9), expiry_date=day(-1))
    stays = world.subscription(world.make_plan(auto_close=False), start_date=day(-9), expiry_date=day(-1))
    auto_close_expired_subscriptions()
    get = lambda s: world.client.get(f"/subscriptions/{s['id']}", headers=world.staff).json()["status"]
    assert (get(closes), get(stays)) == ("closed", "active")


def test_customer_manages_own_subscription_and_addons(world):
    c = world.client
    addon = world.make_product("500", type="Add-on")
    sub = world.subscription()
    assert c.post(f"/portal/subscriptions/{sub['id']}/pause", headers=world.bob_h).status_code == 404
    assert c.post(f"/portal/subscriptions/{sub['id']}/pause", headers=world.alice_h).json()["status"] == "paused"
    c.post(f"/portal/subscriptions/{sub['id']}/resume", headers=world.alice_h)

    assert [a["id"] for a in c.get("/portal/addons", headers=world.alice_h).json()] == [addon["id"]]
    with_addon = c.post(f"/portal/subscriptions/{sub['id']}/addons", headers=world.alice_h,
                        json={"product_id": addon["id"], "unit_price": "1"}).json()
    line = next(l for l in with_addon["lines"] if l["product_id"] == addon["id"])
    assert Decimal(line["unit_price"]) == Decimal("500.00")  # customers cannot set the price
    assert Decimal(world.invoice(sub, confirm=False)["subtotal"]) == Decimal("1500.00")
    off = c.delete(f"/portal/subscriptions/{sub['id']}/addons/{line['id']}", headers=world.alice_h)
    assert len(off.json()["lines"]) == 1


# ── Billing ───────────────────────────────────────────────────────────────────

def test_variant_price_is_billed(world):
    variant = world.client.post(f"/products/{world.product['id']}/variants", headers=world.admin,
                                json={"label": "Odoo", "price_delta": "560"}).json()
    invoice = world.invoice(world.subscription(variant_id=variant["id"]), confirm=False)
    assert Decimal(invoice["subtotal"]) == Decimal("1560.00")
    assert invoice["lines"][0]["description"].endswith("(Odoo)")


def test_nothing_billed_twice_and_cancelled_invoice_can_be_reissued(world):
    c = world.client
    sub = world.subscription()
    first = world.invoice(sub)
    assert c.post(f"/invoices/generate/{sub['id']}", headers=world.staff).status_code == 400
    c.post(f"/invoices/{first['id']}/cancel", headers=world.staff)
    again = c.post(f"/invoices/generate/{sub['id']}", headers=world.staff)
    assert again.status_code == 201 and again.json()["period_start"] == first["period_start"]


def test_only_active_subscriptions_are_invoiced(world):
    sub = world.subscription(state="confirmed")
    assert world.client.post(f"/invoices/generate/{sub['id']}", headers=world.staff).status_code == 400


def test_billing_cycle_confirms_keeps_going_and_is_repeatable(world):
    good = [world.subscription() for _ in range(3)]
    real = billing_tasks.InvoicingService.generate_for_subscription
    calls = []

    def flaky(self, subscription_id, **kwargs):
        calls.append(subscription_id)
        if len(calls) == 1:
            raise RuntimeError("one bad record")
        return real(self, subscription_id, **kwargs)

    with mock.patch.object(billing_tasks.InvoicingService, "generate_for_subscription", flaky):
        result = run_billing_cycle()
    assert len(result["failed"]) == 1 and len(result["success"]) == 2

    result = run_billing_cycle()  # the failed one is picked up, nothing is repeated
    assert len(result["success"]) == 1
    run_billing_cycle()
    world.db.expire_all()
    assert world.db.query(Invoice).count() == len(good)
    assert {i.status.value for i in world.db.query(Invoice).all()} == {"confirmed"}


def test_expired_and_future_subscriptions_are_not_billed(world):
    world.subscription(start_date=day(-20), expiry_date=day(-1))
    world.subscription(start_date=day(10))
    run_billing_cycle()
    assert world.db.query(Invoice).count() == 0


def test_billing_day_is_kept_through_short_months():
    start = date(2027, 1, 31)
    feb = next_billing_date_for(BillingInterval.monthly, start, anchor=start)
    assert feb == date(2027, 2, 28)
    assert next_billing_date_for(BillingInterval.monthly, feb, anchor=start) == date(2027, 3, 31)


# ── Discounts ─────────────────────────────────────────────────────────────────

def test_tax_is_charged_on_the_discounted_amount(world):
    world.discount(value="10")
    assert Decimal(world.invoice(confirm=False)["grand_total"]) == Decimal("1062.00")


def test_subscription_discount_applies_once_and_uses_one_redemption(world):
    addon = world.make_product("1000")
    limited = world.discount(type="fixed", value="100", max_uses=5)
    sub = world.subscription(lines=[
        {"product_id": world.product["id"]}, {"product_id": addon["id"]},
    ])
    assert Decimal(world.invoice(sub, confirm=False)["discount_total"]) == Decimal("100.00")
    d = world.client.get(f"/discounts/{limited['id']}", headers=world.admin).json()
    assert d["used_count"] == 1


def test_total_never_goes_negative(world):
    world.discount(value="70")
    world.discount(value="70")
    assert Decimal(world.invoice(confirm=False)["grand_total"]) >= 0


def test_discount_can_target_one_customer(world):
    world.discount(customer_id=str(world.alice.id))
    theirs = world.invoice(world.subscription(), confirm=False)
    others = world.invoice(world.subscription(customer=world.bob), confirm=False)
    assert (Decimal(theirs["discount_total"]), Decimal(others["discount_total"])) == (Decimal("100.00"), Decimal("0.00"))


def test_cancelling_gives_the_use_back(world):
    limited = world.discount(max_uses=1)
    invoice = world.invoice(confirm=False)
    world.client.post(f"/invoices/{invoice['id']}/cancel", headers=world.staff)
    d = world.client.get(f"/discounts/{limited['id']}", headers=world.admin).json()
    assert (d["used_count"], d["is_active"]) == (0, True)


@pytest.mark.parametrize("body", [
    {"type": "percentage", "value": "150"},
    {"type": "fixed", "value": "-1"},
    {"type": "fixed", "value": "5", "end_date": day(-5)},
])
def test_bad_discounts_rejected(world, body):
    full = {"name": "x", "start_date": day(), "scope": "subscription", **body}
    assert world.client.post("/discounts", headers=world.admin, json=full).status_code == 422


# ── Payments ──────────────────────────────────────────────────────────────────

def test_partial_payments_reconcile(world):
    invoice = world.invoice()
    assert world.pay(invoice["id"], "500").status_code == 201
    middle = world.client.get(f"/invoices/{invoice['id']}", headers=world.staff).json()
    assert (middle["status"], Decimal(middle["balance_due"])) == ("confirmed", Decimal("680.00"))
    world.pay(invoice["id"], "680")
    done = world.client.get(f"/invoices/{invoice['id']}", headers=world.staff).json()
    assert (done["status"], Decimal(done["balance_due"])) == ("paid", Decimal("0.00"))


@pytest.mark.parametrize("amount,code", [("0", 422), ("-5", 422), ("99999", 400)])
def test_bad_amounts_rejected(world, amount, code):
    assert world.pay(world.invoice()["id"], amount).status_code == code


def test_payments_only_on_open_invoices(world):
    draft = world.invoice(confirm=False)
    assert world.pay(draft["id"], "1").status_code == 400
    paid = world.invoice(world.subscription())
    world.pay(paid["id"], paid["grand_total"])
    assert world.pay(paid["id"], "1").status_code == 400


def test_editing_a_payment_updates_the_invoice(world):
    invoice = world.invoice()
    payment = world.pay(invoice["id"], invoice["grand_total"]).json()
    world.client.patch(f"/payments/{payment['id']}", headers=world.staff, json={"amount": "1"})
    assert world.client.get(f"/invoices/{invoice['id']}", headers=world.staff).json()["status"] == "confirmed"


def test_partly_paid_invoice_cannot_be_cancelled(world):
    invoice = world.invoice()
    world.pay(invoice["id"], "1")
    assert world.client.post(f"/invoices/{invoice['id']}/cancel", headers=world.staff).status_code == 400


def test_email_failure_is_reported(world):
    invoice = world.invoice()
    with mock.patch("app.api.invoices.send_email", return_value=False):
        assert world.client.post(f"/invoices/{invoice['id']}/send", headers=world.staff).status_code == 502


# ── Reports ───────────────────────────────────────────────────────────────────

def test_summary_counts_money_received_and_real_balances(world):
    invoice = world.invoice()
    world.pay(invoice["id"], "180")
    summary = world.client.get("/reports/summary", headers=world.staff).json()
    assert summary["total_revenue_this_month"] == 180.0
    assert summary["outstanding_amount"] == 1000.0
    assert summary["active_subscription_count"] == 1


def test_paging_is_bounded_and_totals_are_exposed(world):
    world.subscription(state="draft")
    r = world.client.get("/subscriptions?limit=1", headers=world.staff)
    assert r.headers["X-Total-Count"] == "1"
    assert world.client.get("/invoices?limit=-1", headers=world.staff).status_code == 422




def test_subscriptions_and_invoices_can_be_searched(world):
    sub = world.subscription()
    run_billing_cycle()
    other = world.client.post("/subscriptions", headers=world.staff, json={
        "customer_id": str(world.bob.id), "plan_id": world.plan["id"],
    }).json()

    found = world.client.get("/subscriptions", headers=world.staff,
                             params={"search": sub["subscription_number"]}).json()
    assert [s["id"] for s in found] == [sub["id"]]
    found = world.client.get("/subscriptions", headers=world.staff, params={"search": world.bob.email}).json()
    assert [s["id"] for s in found] == [other["id"]]

    number = world.client.get("/invoices", headers=world.staff).json()[0]["invoice_number"]
    found = world.client.get("/invoices", headers=world.staff, params={"search": number}).json()
    assert [i["invoice_number"] for i in found] == [number]
    found = world.client.get("/invoices", headers=world.staff, params={"search": world.alice.email}).json()
    assert [i["invoice_number"] for i in found] == [number]
    assert world.client.get("/invoices", headers=world.staff, params={"search": "nothing"}).json() == []


def test_report_by_plan_counts_subscriptions_and_money_received(world):
    world.subscription()
    run_billing_cycle()
    invoice = world.client.get("/invoices", headers=world.staff).json()[0]
    world.client.post(f"/invoices/{invoice['id']}/confirm", headers=world.staff)
    world.client.post("/payments", headers=world.staff, json={
        "invoice_id": invoice["id"], "amount": "100.00", "method": "upi", "payment_date": day(),
    })

    rows = world.client.get("/reports/by-plan", headers=world.staff,
                            params={"from": day(-1), "to": day()}).json()
    row = next(r for r in rows if r["plan_id"] == world.plan["id"])
    assert (row["active"], row["paused"], row["closed"], row["received"]) == (1, 0, 0, 100.0)
    assert world.client.get("/reports/by-plan", headers=world.alice_h,
                            params={"from": day(-1), "to": day()}).status_code == 403


def test_monthly_recurring_revenue_normalises_billing_periods(world):
    yearly = world.make_plan(billing_interval="yearly", price="12000")
    world.subscription()
    world.subscription(plan_=yearly)
    world.subscription(state="draft")

    summary = world.client.get("/reports/summary", headers=world.staff).json()
    assert summary["monthly_recurring_revenue"] == 2000.0  # 1000 a month + 12000 a year, not the draft

    only_yearly = world.client.get("/reports/summary", headers=world.staff, params={"plan_id": yearly["id"]}).json()
    assert only_yearly["monthly_recurring_revenue"] == 1000.0

    rows = world.client.get("/reports/by-plan", headers=world.staff, params={"from": day(), "to": day()}).json()
    assert next(r for r in rows if r["plan_id"] == yearly["id"])["mrr"] == 1000.0


def test_email_refuses_to_send_a_password_unencrypted():
    from app.utils import email as email_module

    server = mock.MagicMock()
    server.__enter__.return_value = server
    server.has_extn.return_value = False
    with mock.patch.object(email_module.smtplib, "SMTP", return_value=server), \
            mock.patch.object(email_module.settings, "SMTP_USER", "me@gmail.com"):
        assert email_module.send_email("a@example.com", "Hi", "Body") is False
    server.login.assert_not_called()
    server.sendmail.assert_not_called()
