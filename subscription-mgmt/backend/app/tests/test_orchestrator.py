import time
from uuid import uuid4
from unittest.mock import MagicMock, patch

from app.isse.schemas import CheckoutContext, Decision, RuleVerdict
from app.isse.orchestrator import RiskOrchestrator


def _ctx():
    return CheckoutContext(request_id=uuid4(), ip_address="9.9.9.9", plan_id=uuid4())


@patch("app.isse.orchestrator.settings")
@patch("app.isse.orchestrator.score_card_testing_risk")
@patch("app.isse.orchestrator.run_all_rules")
def test_ai_timeout_falls_back_to_rules_only(mock_rules, mock_ai, mock_settings):
    mock_rules.return_value = [
        RuleVerdict(rule_id="VELOCITY_SIGNUP", decision=Decision.ALLOW, reason="ok", triggered=False)
    ]
    mock_ai.side_effect = lambda *a, **kw: time.sleep(5)
    mock_settings.ai_timeout_ms = 50

    orchestrator = RiskOrchestrator()
    db = MagicMock()
    decision = orchestrator.evaluate(_ctx(), db)

    assert decision.decision == Decision.ALLOW
    assert any(r.degraded for r in decision.ai_results)