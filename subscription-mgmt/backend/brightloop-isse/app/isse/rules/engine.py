from sqlalchemy.orm import Session
from app.isse.schemas import CheckoutContext, RuleVerdict, Decision
from app.isse.rules import velocity, geo_mismatch, trial_abuse, integrity

_SEVERITY = {Decision.ALLOW: 0, Decision.CHALLENGE: 1, Decision.REVIEW: 2, Decision.BLOCK: 3}


def run_all_rules(ctx: CheckoutContext, db: Session) -> list[RuleVerdict]:
    return [
        velocity.check_signup_velocity(ctx),
        velocity.check_card_attempt_velocity(ctx),
        geo_mismatch.check_geo_billing_mismatch(ctx),
        trial_abuse.check_trial_abuse(ctx, db),
        integrity.check_price_integrity(ctx, db),
        integrity.check_idempotency(ctx),
    ]


def worst_rule_decision(results: list[RuleVerdict]) -> tuple[Decision, str]:
    worst = max(results, key=lambda r: _SEVERITY[r.decision])
    return worst.decision, (worst.reason if worst.triggered else "all_rules_passed")