import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from sqlalchemy.orm import Session

from app.isse.config import settings
from app.isse.schemas import CheckoutContext, RiskDecision, Decision, AIVerdict
from app.isse.rules.engine import run_all_rules, worst_rule_decision
from app.isse.ai.card_testing_model import score_card_testing_risk
from app.isse.models_sql import RiskAuditLog

logger = logging.getLogger("isse.orchestrator")
_executor = ThreadPoolExecutor(max_workers=8)
_SEVERITY = {Decision.ALLOW: 0, Decision.CHALLENGE: 1, Decision.REVIEW: 2, Decision.BLOCK: 3}


class RiskOrchestrator:
    """
    Combines the deterministic rule layer and adaptive AI layer into one decision.
    Rules run first and short-circuit on BLOCK (cheapest path, no AI call needed).
    AI always runs under a strict timeout; on timeout/error it degrades to
    rules-only instead of failing open or closed.
    """

    def evaluate(self, ctx: CheckoutContext, db: Session) -> RiskDecision:
        rule_results = run_all_rules(ctx, db)
        rule_decision, rule_reason = worst_rule_decision(rule_results)

        if rule_decision == Decision.BLOCK:
            return self._finalize(ctx, db, rule_decision, rule_reason, rule_results, [])

        ai_results = self._run_ai_layer(ctx, db)
        ai_decision, ai_reason = self._worst_ai_decision(ai_results)

        final_decision = max([rule_decision, ai_decision], key=lambda d: _SEVERITY[d])
        final_reason = ai_reason if _SEVERITY[ai_decision] >= _SEVERITY[rule_decision] else rule_reason

        return self._finalize(ctx, db, final_decision, final_reason, rule_results, ai_results)

    def _run_ai_layer(self, ctx: CheckoutContext, db: Session) -> list[AIVerdict]:
        future = _executor.submit(score_card_testing_risk, ctx, db)
        try:
            return [future.result(timeout=settings.ai_timeout_ms / 1000)]
        except (FutureTimeoutError, Exception) as exc:
            logger.warning("ISSE AI layer degraded: %s", exc)
            return [AIVerdict(model="card_testing_gbm", score=0.0, decision=Decision.ALLOW,
                               reason="ai_layer_timeout_or_error_fallback_to_rules", degraded=True)]

    @staticmethod
    def _worst_ai_decision(results: list[AIVerdict]) -> tuple[Decision, str]:
        worst = max(results, key=lambda r: _SEVERITY[r.decision])
        return worst.decision, worst.reason

    def _finalize(self, ctx, db, decision, reason, rule_results, ai_results) -> RiskDecision:
        self._write_audit(ctx, db, decision, reason, rule_results, ai_results)
        return RiskDecision(request_id=ctx.request_id, decision=decision, reason=reason,
                             rule_results=rule_results, ai_results=ai_results)

    @staticmethod
    def _write_audit(ctx, db: Session, decision, reason, rule_results, ai_results):
        triggered_rule = next((r.rule_id for r in rule_results if r.triggered), None)
        top_ai = ai_results[0] if ai_results else None

        db.add(RiskAuditLog(
            request_id=ctx.request_id,
            account_id=ctx.account_id,
            decision=decision.value,
            layer="ORCHESTRATOR",
            rule_id=triggered_rule,
            ai_model=top_ai.model if top_ai else None,
            ai_score=top_ai.score if top_ai else None,
            reason=reason,
            context=ctx.model_dump(mode="json"),
        ))
        db.commit()


risk_orchestrator = RiskOrchestrator()