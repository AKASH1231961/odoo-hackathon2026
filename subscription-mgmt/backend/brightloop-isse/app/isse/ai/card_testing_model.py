import os
import joblib
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.isse.config import settings
from app.isse.schemas import CheckoutContext, AIVerdict, Decision

_MODEL_PATH = os.path.join(settings.model_artifact_dir, "card_testing_gbm.joblib")
_model = None


def _load_model():
    global _model
    if _model is None and os.path.exists(_MODEL_PATH):
        _model = joblib.load(_MODEL_PATH)
    return _model


def _extract_features(ctx: CheckoutContext, db: Session) -> np.ndarray:
    distinct_cards_per_device = 0
    if ctx.device_fingerprint:
        distinct_cards_per_device = db.execute(text("""
            SELECT COUNT(DISTINCT card_fingerprint) FROM card_fingerprints
            WHERE device_fingerprint = :fp AND created_at > now() - interval '1 hour'
        """), {"fp": ctx.device_fingerprint}).scalar() or 0

    distinct_cards_per_ip = db.execute(text("""
        SELECT COUNT(DISTINCT card_fingerprint) FROM card_fingerprints
        WHERE ip_address = :ip AND created_at > now() - interval '1 hour'
    """), {"ip": ctx.ip_address}).scalar() or 0

    decline_ratio = db.execute(text("""
        SELECT COALESCE(SUM(CASE WHEN outcome = 'declined' THEN 1 ELSE 0 END), 0)::float
               / GREATEST(COUNT(*), 1)
        FROM card_fingerprints
        WHERE card_fingerprint = :cfp AND created_at > now() - interval '24 hours'
    """), {"cfp": ctx.card_fingerprint}).scalar() or 0.0

    return np.array([[distinct_cards_per_device, distinct_cards_per_ip, decline_ratio]])


def score_card_testing_risk(ctx: CheckoutContext, db: Session) -> AIVerdict:
    model = _load_model()
    features = _extract_features(ctx, db)

    if model is None:
        fan_out = features[0][0] + features[0][1]
        score = min(1.0, fan_out / 10.0)
        degraded = True
    else:
        score = float(model.predict_proba(features)[0][1])
        degraded = False

    if score >= settings.card_testing_block_threshold:
        decision = Decision.BLOCK
    elif score >= settings.card_testing_challenge_threshold:
        decision = Decision.CHALLENGE
    else:
        decision = Decision.ALLOW

    return AIVerdict(model="card_testing_gbm", score=round(score, 5), decision=decision,
                      reason=f"card_testing_score={score:.3f}", degraded=degraded)