from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine
from app.core.config import settings
from app import models  # noqa: F401 — registers all ORM models on Base.metadata

from app.api import (
    auth,
    users,
    products,
    plans,
    quotation_templates,
    subscriptions,
    tax_rules,
    discounts,
    invoices,
    payments,
    portal,
    reports,
)

app = FastAPI(
    title="Brightloop Subscription Management System",
    version="1.0.0",
    description="Full-lifecycle subscription billing platform: plans, subscriptions, invoices, payments.",
)

# CORS — allow all origins in dev; restrict to FRONTEND_URL in production
origins = (
    ["*"]
    if settings.ENVIRONMENT == "development"
    else [settings.FRONTEND_URL]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """
    Create all tables on startup.
    For production, switch to Alembic migrations (alembic upgrade head).
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print(f"[startup] Database connection deferred/skipped in local env: {exc}")


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "version": "1.0.0"}


# ── Register routers ──────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(plans.router)
app.include_router(quotation_templates.router)
app.include_router(subscriptions.router)
app.include_router(tax_rules.router)
app.include_router(discounts.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(portal.router)
app.include_router(reports.router)

