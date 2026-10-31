import os
import joblib
import pandas as pd
from app.isse.config import settings

_MODEL_PATH = os.path.join(settings.model_artifact_dir, "usage_anomaly_iforest.joblib")
FEATURE_COLS = ["api_calls_per_hour", "seat_delta", "storage_growth_mb", "off_hours_ratio"]


def load_usage_model():
    return joblib.load(_MODEL_PATH) if os.path.exists(_MODEL_PATH) else None


def score_tenant_usage(df: pd.DataFrame) -> pd.DataFrame:
    """df must contain tenant_id + FEATURE_COLS."""
    model = load_usage_model()

    if model is None:
        df["anomaly_score"] = 0.0
        df["is_anomalous"] = False
        return df

    raw_scores = -model.score_samples(df[FEATURE_COLS].values)  # higher = more anomalous
    normalized = (raw_scores - raw_scores.min()) / (raw_scores.ptp() + 1e-9)
    df["anomaly_score"] = normalized
    df["is_anomalous"] = df["anomaly_score"] >= settings.usage_anomaly_alert_threshold
    return df