import os
import joblib
import pandas as pd
from app.isse.config import settings

_MODEL_PATH = os.path.join(settings.model_artifact_dir, "churn_gbm.joblib")
FEATURE_COLS = [
    "usage_trend_30d", "support_tickets_90d", "avg_payment_delay_days",
    "downgrade_count", "login_frequency_decay",
]


def load_churn_model():
    return joblib.load(_MODEL_PATH) if os.path.exists(_MODEL_PATH) else None


def score_subscriptions(df: pd.DataFrame) -> pd.DataFrame:
    model = load_churn_model()
    df["churn_risk_score"] = (
        model.predict_proba(df[FEATURE_COLS].values)[:, 1] if model else 0.0
    )
    df["churn_risk_band"] = pd.cut(
        df["churn_risk_score"],
        bins=[-0.01, 0.3, settings.churn_high_risk_threshold, 1.0],
        labels=["low", "medium", "high"],
    )
    return df