from sqlalchemy.orm import Session
from sqlalchemy import or_, text
from app.isse.models_sql import TrialUsage
from app.isse.schemas import CheckoutContext, RuleVerdict, Decision

DISPOSABLE_DOMAIN_CACHE: set[str] = set()


def load_disposable_domains(db: Session):
    """Call once at app startup to warm the in-memory cache."""
    rows = db.execute(text("SELECT domain FROM disposable_email_domains")).fetchall()
    DISPOSABLE_DOMAIN_CACHE.clear()
    DISPOSABLE_DOMAIN_CACHE.update(r[0] for r in rows)


def check_trial_abuse(ctx: CheckoutContext, db: Session) -> RuleVerdict:
    if not ctx.is_trial:
        return RuleVerdict(rule_id="TRIAL_ABUSE", decision=Decision.ALLOW,
                            reason="not_a_trial_request", triggered=False)

    email_domain = (ctx.email or "").split("@")[-1].lower() if ctx.email else None

    conditions = []
    if ctx.device_fingerprint:
        conditions.append(TrialUsage.device_fingerprint == ctx.device_fingerprint)
    if ctx.card_fingerprint:
        conditions.append(TrialUsage.card_fingerprint == ctx.card_fingerprint)

    if conditions:
        existing = (
            db.query(TrialUsage)
            .filter(TrialUsage.consumed.is_(True))
            .filter(or_(*conditions))
            .first()
        )
        if existing:
            return RuleVerdict(rule_id="TRIAL_ABUSE", decision=Decision.BLOCK,
                                reason="device_or_card_already_used_trial", triggered=True)

    if email_domain and email_domain in DISPOSABLE_DOMAIN_CACHE:
        return RuleVerdict(rule_id="TRIAL_ABUSE", decision=Decision.BLOCK,
                            reason=f"disposable_email_domain:{email_domain}", triggered=True)

    return RuleVerdict(rule_id="TRIAL_ABUSE", decision=Decision.ALLOW,
                        reason="no_prior_trial_signal", triggered=False)