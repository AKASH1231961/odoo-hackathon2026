"""
Adaptive AI supervision layer: card-testing/botnet scoring, usage anomaly
detection, churn prediction, and smart dunning retry scheduling.

Note: train/ is intentionally NOT imported here — training scripts pull in
heavier deps (full sklearn training stack, DB creds for read-replica/warehouse)
that shouldn't be a runtime dependency of the API/worker containers.
"""

from app.isse.ai.card_testing_model import score_card_testing_risk
from app.isse.ai.usage_anomaly_model import score_tenant_usage
from app.isse.ai.churn_model import score_subscriptions
from app.isse.ai.dunning_bandit import recommend_retry_slot, record_outcome
from app.isse.ai.feature_store import OnlineFeatureStore

__all__ = [
    "score_card_testing_risk",
    "score_tenant_usage",
    "score_subscriptions",
    "recommend_retry_slot",
    "record_outcome",
    "OnlineFeatureStore",
]