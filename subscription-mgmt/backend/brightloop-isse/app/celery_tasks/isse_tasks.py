"""
Register these alongside the existing Celery Beat schedule in celery_app.py.
"""
import os
import pandas as pd
from celery import shared_task
from sqlalchemy import create_engine

from app.isse.ai.churn_model import score_subscriptions
from app.isse.ai.usage_anomaly_model import score_tenant_usage
from app.isse.ai.dunning_bandit import recommend_retry_slot, record_outcome

DB_URL = os.environ["DATABASE_URL"]


@shared_task(name="isse.score_churn_risk_nightly")
def score_churn_risk_nightly():
    engine = create_engine(DB_URL)
    df = pd.read_sql("SELECT * FROM subscription_churn_features_view", engine)
    scored = score_subscriptions(df)
    scored[["subscription_id", "churn_risk_score", "churn_risk_band"]].to_sql(
        "subscription_churn_scores", engine, if_exists="replace", index=False
    )
    return {"scored_count": len(scored)}


@shared_task(name="isse.detect_usage_anomalies_hourly")
def detect_usage_anomalies_hourly():
    engine = create_engine(DB_URL)
    df = pd.read_sql("SELECT * FROM tenant_usage_hourly_view", engine)
    scored = score_tenant_usage(df)
    anomalies = scored[scored["is_anomalous"]]
    # TODO: wire into existing alerting pipeline for flagged tenants
    return {"anomalous_tenants": anomalies["tenant_id"].tolist()}


@shared_task(name="isse.schedule_smart_dunning_retry")
def schedule_smart_dunning_retry(invoice_id: str):
    dow, hour = recommend_retry_slot()
    # TODO: enqueue the actual retry attempt task with an eta matching this slot
    return {"invoice_id": invoice_id, "recommended_day_of_week": dow, "recommended_hour": hour}


@shared_task(name="isse.record_dunning_outcome")
def record_dunning_outcome(day_of_week: int, hour: int, success: bool):
    record_outcome(day_of_week, hour, success)