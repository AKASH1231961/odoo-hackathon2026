import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.isse.schemas import CheckoutContext
from app.isse.middleware import enforce_risk_check
from app.services.invoicing_service import InvoicingService  # existing Brightloop service
from app.services.payment_service import PaymentService      # existing Brightloop service

router = APIRouter(prefix="/api/checkout", tags=["checkout"])


@router.post("/subscribe")
def checkout_subscribe(payload: dict, request: Request, db: Session = Depends(get_db)):
    ctx = CheckoutContext(
        request_id=uuid.uuid4(),
        account_id=payload.get("account_id"),
        ip_address=request.client.host,
        device_fingerprint=payload.get("device_fingerprint"),
        card_fingerprint=payload.get("card_fingerprint"),
        billing_country=payload.get("billing_country"),
        card_avs_result=payload.get("card_avs_result"),
        email=payload.get("email"),
        plan_id=payload["plan_id"],
        requested_price=payload.get("requested_price"),
        is_trial=payload.get("is_trial", False),
        idempotency_key=request.headers.get("Idempotency-Key"),
    )

    # raises HTTPException(403/428) if BLOCKed/CHALLENGEd; returns a RiskDecision on ALLOW/REVIEW
    risk_decision = enforce_risk_check(ctx, db)

    payment = PaymentService.create_payment_intent(db, payload)
    subscription, invoice = InvoicingService.create_subscription_with_invoice(db, payload, payment)

    return {
        "subscription_id": subscription.id,
        "invoice_id": invoice.id,
        "risk_flagged_for_review": risk_decision.decision == "REVIEW",
    }