from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session
from app.core.database import get_db
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

# Authentication is by bearer token, so browsers need no credentialed CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    """Keep `detail` a readable string; the field-by-field list is in `errors`."""
    errors = [
        {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
        for e in exc.errors()
    ]
    detail = "; ".join(f"{e['field']}: {e['message']}" if e["field"] else e["message"] for e in errors)
    return JSONResponse(status_code=422, content={"detail": detail, "errors": errors})


@app.exception_handler(IntegrityError)
async def integrity_error(_: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={"detail": "That change conflicts with existing data or refers to a missing record"},
    )


@app.exception_handler(DataError)
async def data_error(_: Request, exc: DataError):
    return JSONResponse(status_code=400, content={"detail": "A value is out of range or invalid"})


@app.get("/health", tags=["System"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
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

